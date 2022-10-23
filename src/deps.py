
from typing import Any, Callable, List, Tuple
import json
import logging
from packaging import version
from pathlib import Path
import subprocess
from tqdm.contrib.concurrent import thread_map
import os
import shlex

from .data import CompileTarget, DependencyMap

def extract_deps(cmd, process: Callable[[CompileTarget], Any]):
    '''
    Extracts a list of targets from a compile command entry.
    The result is passed to the `process` callback.
    '''
    def get_deps_raw(command: str, cwd: str) -> str:
        '''
        Invokes the compiler with extra flags to yield a list of dependencies.
        Returns the captured output without any processing.
        '''
        deps_cmd = shlex.split(command) + ["-MM", "-MF", "-"]
        return subprocess.check_output(deps_cmd, cwd=cwd).decode('utf-8')

    def parse_deps_raw(deps_raw: str) -> Tuple[str, List[str]]:
        '''
        Parses a deps output from a compilar.
        Throws a ValueError if a semicolon is missing.
        '''
        [target, deps_blob] = deps_raw.split(":")
        deps = deps_blob.replace("\\", " ").split()
        return (target, deps)

    try:
        deps_raw = get_deps_raw(cmd["command"], cmd["directory"])
        try:
            [target, deps] = parse_deps_raw(deps_raw)
            process(CompileTarget(cmd["file"], target, deps))
        except ValueError:
            logging.error(f"Failed to parse deps of {cmd['file']}")
    except subprocess.CalledProcessError:
        logging.error(f"Failed to fetch deps of {cmd['file']}")


def verify_ninja_version(ninja_binary: str):
    version_str = subprocess.check_output(
        [ninja_binary, "--version"]).decode("utf-8")
    assert version.parse(version_str) >= version.parse("1.11.0")


def get_ninja_target_inputs(ninja_binary: str, ninja_build_dir: str, targets: List[str]):
    verify_ninja_version(ninja_binary)
    logging.debug(f"Calling {ninja_binary} to fetch inputs for "
                  f"{', '.join(targets)} from {ninja_build_dir}")
    cmd = [ninja_binary, "-C", ninja_build_dir, "-t", "inputs", *targets]
    return subprocess.check_output(cmd).decode("utf-8").splitlines()


def gather_deps(ninja_binary: str, build_dir: str, targets: List[str]) -> DependencyMap:
    with open(Path(build_dir).joinpath("compile_commands.json")) as f:
        compile_commands = json.load(f)

    logging.info(f"Found {len(compile_commands)} compile commands")
    for cmd in compile_commands:
        logging.debug(cmd["file"])

    target_inputs = get_ninja_target_inputs(ninja_binary, build_dir, targets)
    logging.info(
        f"Found {len(target_inputs)} inputs required to build {', '.join(targets)}")
    for target in targets:
        logging.debug(target)

    # Convert paths to absolute paths
    normalize = lambda path: os.path.normpath(os.path.join(build_dir, path))
    target_inputs_abs = set(normalize(f) for f in target_inputs)

    target_compile_commands = [
        cmd for cmd in compile_commands if cmd["file"] in target_inputs_abs]
    logging.info(f"{len(target_compile_commands)} of the {len(compile_commands)} "
                 "compile commands are required to build the requested targets.")
    for cmd in target_compile_commands:
        logging.debug(cmd["file"])

    mapping = DependencyMap()

    thread_map(lambda cmd: extract_deps(
        cmd, mapping.process), target_compile_commands)

    return mapping
