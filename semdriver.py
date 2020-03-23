#!/usr/bin/env python3

from syn import Parser
from sem import analysis, output


def run(f):
    parser = Parser(f, error_handler=output)
    result = parser.start()
    if result.success:
        analyzer = analysis.SemanticAnalyzer(result.ast, output=output)
        analyzer.start()
        output.success()
    else:
        print(f.name + ": Failed to parse")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        usage="Parses and generates the symbol tables of a given source file"
    )
    parser.add_argument("file", type=argparse.FileType("r"), help="Source file")
    args = parser.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
