import argparse

from lex import Scanner
from lex.output import TokenOutput

parser = argparse.ArgumentParser()
parser.add_argument("file", help="Source file")


def main():
    args = parser.parse_args()
    scanner = Scanner(open(args.file, "r"))
    out = TokenOutput(args.file)
    for token in scanner:
        out.write(token)


if __name__ == "__main__":
    main()
