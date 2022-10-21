# hpp-ray

Currently, hpp-ray analyzes the number of C/C++ translation units affected by touching a header file.

The overall aim for this tool is to aid in compile time optimization by estimating the long-term impact of changes on individual header files.

## Requirements

Your system needs to have Ninja 1.11 or later.
Given that it's not yet available via `apt` or `pip`, the implementation is assuming the binary's in the root directory of `hpp-ray`.

The project under analysis needs to be configured with CMake and Ninja.
The build folder must contain files `compile_commands.json` and `build.ninja`.

## Getting started

TODO: add `setup.py`

1. Install `click` and `tqdm`.

2. Configure the application you'd like to analyze. Set Ninja as your generator.
```sh
mkdir build && cd build
cmake .. -G Ninja
```

3. Run `python hpp-ray.py ~/project/build tests`.
This analyzes which headers cause the most recompilations when touched.

## Does it solve a different problem than `include-what-you-use`?

Yes. Consider a config structure with getter and setter methods used by 1k translation units.
IWYU will not optimize this, as you need a full definition of a structure to invoke a method on it.

However, it *is* possible to optimize this - e.g. by using external getter wrappers, and then declaring them locally.
`hpp-ray` will simply help you decide if it's worth the effort.

## Things I want to add

### Git cross-check

OK, cool, this header causes 10k files to recompile, but maybe it was last touched 3 years ago?

I want to run some analysis on the repo to work out what the actual impact is of a header file on the day-to-day work of the developers.
The impact score would be amended by how many times the file was modified in a given timeframe.

### Compile time profiling

OK, cool, this header is causing 1k files to recompile every day, but maybe they're tiny C files and it takes a minute?

For each compile command, I want to collect data on how long it takes to execute.
The impact score of a dependency would be amended by this figure.
