import argparse

from lex import Scanner
from lex.output import TokenOutput

parser = argparse.ArgumentParser()
parser.add_argument("file", type=argparse.FileType('r'), help="Source file")


def main():
    args = parser.parse_args()
    scanner = Scanner(args.file)
    out = TokenOutput(args.file.name)
    for token in scanner:
        out.write(token)


if __name__ == "__main__":
    main()
