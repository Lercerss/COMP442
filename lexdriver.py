#!/usr/bin/env python3

from lex import Scanner
from lex.output import TokenOutput


def run(f):
    scanner = Scanner(f)
    out = TokenOutput(f.name)
    for token in scanner:
        out.write(token)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        usage="Performs lexical analysis of a given source file"
    )
    parser.add_argument("file", type=argparse.FileType("r"), help="Source file")
    args = parser.parse_args()
    run(args.file)


if __name__ == "__main__":
    main()
