#!/usr/bin/env python3

import os
from syndriver import run


def main():
    to_run = []
    for _, _, filenames in os.walk("test/syn/src/"):
        for filename in filenames:
            if filename.endswith(".src"):
                to_run.append("test/syn/src/" + filename)
    for f in to_run:
        with open(f) as f_:
            print("Parsing {}".format(f))
            run(f_)
        print("-----------------------")

        print("Output at:\n" + f.replace(".src", ".outast"))
        print(f.replace(".src", ".outderivation"))
        print(f.replace(".src", ".outderivation.var"))
        print("----------------------------------------------")


if __name__ == "__main__":
    main()

