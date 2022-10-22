#!/bin/python3

import click
import logging
from os.path import realpath

from . import deps

logging.basicConfig(
    format="%(levelname)-10s %(message)s", level=logging.INFO)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--ninja-binary", "-b", type=str, default=None)
@click.option("--num-files", "-n", help="top N loudest headers", type=int, default=10)
@click.argument("build-dir")
@click.argument("targets", nargs=-1)
def gather_deps(ninja_binary, num_files, build_dir, targets):
    '''
    Process `build.ninja` and `compile_commands.json`.
    Amend the compile commands to make the compiler produce dependency lists.
    Process those lists to create a mapping from files to compile targets.
    '''
    ninja_binary = realpath(ninja_binary) if ninja_binary else "ninja"
    if not targets:
        logging.warn("No targets were specified, assuming `all`.")
        targets = ["all"]

    mapping = deps.gather_deps(ninja_binary, build_dir, targets)

    for [k, v] in mapping.sorted_items()[:num_files]:
        print(f"{k} contributes to {len(v)} targets")


if __name__ == "__main__":
    cli()
