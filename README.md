# COMP 442 Compiler Design Project

By Lucas Turpin - Winter 2020

## Usage

```bash
./lexdriver.py <src>  # Runs the lexical analyzer on a single source file
./syndriver.py <src>  # Runs the parser on a single source file
./semdriver.py <src>  # Runs the semantic analyzer on a single source file
./gendriver.py <src>  # Runs the code generation on a single source file
./a1_driver.py  # Runs and prints the output of the lexical analyzer on every source file in ./test/lex/src/
./a2_driver.py  # Runs the parser on every source file in ./test/syn/src/
./a3_driver.py  # Runs the semantic analyzer on every source file in ./test/sem/src/
./a4_driver.py  # Runs the code generation on every source file in ./test/fixtures/
```

## Dependencies

- Python 3
- Moon Processor

### Moon Processor

The Moon processor executable can be compiled using [the provided build script](./moon_processor/build.sh).
If it is already installed, the symlink at the root of the repo can be modified.
