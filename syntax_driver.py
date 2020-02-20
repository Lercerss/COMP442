#!/usr/bin/env python3

from syntax import Parser
from syntax.output import ParserOutput


def run(f):
    output = ParserOutput(f.name)
    parser = Parser(f, prodcution_handler=output, error_handler=output)
    result = parser.start()
    if result.success:
        print(f.name + ": No parsing errors found")
    else:
        print(f.name + ": Failed to parse")
    output.ast(result.ast, result.success)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        usage="Parses and generates the AST of a given source file"
    )
    parser.add_argument("file", type=argparse.FileType("r"), help="Source file")
    args = parser.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
