#!/usr/bin/env python3

from phases import PhaseHandler, PHASES


def run(f, phase):
    handler = PhaseHandler(f, phase)
    handler.run()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="COMP 442 Compiler for the Moon simulator",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "PHASE",
        help='One of "{}" or "{}"\n\t{}'.format(
            '", "'.join(list(PHASES.keys())[:-1]),
            list(PHASES.keys())[-1],
            "\n\t".join(k + ": " + v for k, v in PHASES.items()),
        ),
    )
    parser.add_argument(
        "FILE", type=argparse.FileType("r"), help="Source file to compile"
    )
    args = parser.parse_args()
    if args.PHASE not in PHASES:
        print('Invalid PHASE "{}".'.format(args.PHASE))
        parser.print_help()
        exit(1)

    run(args.FILE, args.PHASE)


if __name__ == "__main__":
    main()
