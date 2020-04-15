import re

EXTENSION = re.compile(r"\.src$")


def write(source_file: str, executable: str):
    with open(EXTENSION.sub(".moon", source_file), "w") as f:
        f.write(executable)
