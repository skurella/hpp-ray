#!/bin/python3

from typing import Any, Callable, List, Mapping, Tuple
import click
from dataclasses import dataclass
import json
import logging
from os.path import realpath
from threading import Lock
from pathlib import Path
import subprocess
from tqdm.contrib.concurrent import thread_map

logging.basicConfig(
    format="%(levelname)-10s %(message)s", level=logging.INFO)


@dataclass
class CompileTarget:
    '''A (possibly local) build target with a single compile command.'''
    file: str
    target: str
    compile_deps: List[str]


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
        deps_cmd = command.split(' ') + ["-MM", "-MF", "-"]
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


class DependencyMap:
    '''For each dependency, stores the targets which it comprises.'''
    _map: Mapping[str, List[CompileTarget]] = {}
    _lock = Lock()

    def process(self, target: CompileTarget):
        with self._lock:
            for dep in target.compile_deps:
                if dep not in self._map:
                    self._map[dep] = []
                self._map[dep].append(target)

    def sorted_items(self):
        with self._lock:
            return sorted(self._map.items(), key=lambda item: -len(item[1]))


def get_ninja_target_inputs(ninja_binary: str, ninja_build_dir: str, targets: List[str]):
    logging.debug(f"Calling {ninja_binary} to fetch inputs for "
                  f"{', '.join(targets)} from {ninja_build_dir}")
    cmd = [ninja_binary, "-C", ninja_build_dir, "-t", "inputs", *targets]
    return subprocess.check_output(cmd).decode("utf-8").splitlines()


@click.command()
@click.option("--ninja-binary", "-b", type=str, default="ninja")
@click.option("--num-files", "-n", help="top N loudest headers", type=int, default=10)
@click.argument("build-dir")
@click.argument("targets", nargs=-1)
def analyze_deps(ninja_binary, num_files, build_dir: str, targets: List[str]):
    with open(Path(build_dir).joinpath("compile_commands.json")) as f:
        compile_commands = json.load(f)

    logging.info(f"Found {len(compile_commands)} compile commands")
    for cmd in compile_commands:
        logging.debug(cmd["file"])

    target_inputs = get_ninja_target_inputs(
        realpath(ninja_binary), build_dir, targets)
    logging.info(
        f"Found {len(target_inputs)} inputs required to build {', '.join(targets)}")
    for target in targets:
        logging.debug(target)

    relevant_compile_commands = [
        cmd for cmd in compile_commands if cmd["file"] in target_inputs]
    logging.info(f"{len(relevant_compile_commands)} of the {len(compile_commands)} "
                 "compile commands are required to build the requested targets.")
    for cmd in relevant_compile_commands:
        logging.debug(cmd["file"])

    mapping = DependencyMap()

    thread_map(lambda cmd: extract_deps(
        cmd, mapping.process), relevant_compile_commands)

    for [k, v] in mapping.sorted_items()[:num_files]:
        logging.info(f"{k} contributes to {len(v)} targets")


@click.group()
def cli():
    pass


cli.add_command(analyze_deps)

if __name__ == "__main__":
    cli()
