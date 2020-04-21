import re

EXTENSION = re.compile(r"\.src$")


class ExecutableOutput:
    def __init__(self, source_file):
        self.__moon_file = open(EXTENSION.sub(".moon", source_file), "w")

    def write(self, executable: str):
        self.__moon_file.write(executable)
        self.__moon_file.close()

    def collect_files(self):
        return [self.__moon_file.name]
