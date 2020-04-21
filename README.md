# COMP 442 Compiler Design Project

By Lucas Turpin - Winter 2020

## Usage

```bash
./driver.py <PHASE> <FILE>
```

```text
usage: driver.py [-h] PHASE FILE

COMP 442 Compiler for the Moon simulator

positional arguments:
  PHASE       One of "lex", "syn", "sem", "gen" or "exe"
                lex: Performs lexical analysis
                syn: Performs syntactic analysis
                sem: Performs semantic analysis
                gen: Performs code generation
                exe: Generates and executes the corresponding moon output file
  FILE        Source file to compile

optional arguments:
  -h, --help  show this help message and exit
```

## Dependencies

- Python 3
- Moon Processor

### Moon Processor

The Moon processor executable can be compiled using [the provided build script](./moon_processor/build.sh).
If it is already installed, the symlink at the root of the repo can be modified.
