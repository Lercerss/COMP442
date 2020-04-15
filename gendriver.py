#!/usr/bin/env python3

from syn import Parser
from sem import analysis, output as sem_output
from gen import code, output


def run(f):
    out = sem_output.SemanticOutput()
    parser = Parser(f, error_handler=out)
    result = parser.start()
    if result.success:
        analyzer = analysis.SemanticAnalyzer(result.ast, output=out)
        analyzer.start()
        if out.success(f.name):
            generator = code.Generator(root=result.ast)
            executable = generator.start()
            out.success(f.name)
            output.write(f.name, executable)
    else:
        out.fail(f.name)


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