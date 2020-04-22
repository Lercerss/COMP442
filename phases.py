from lex import output as lex_out, Scanner
from syn import output as syn_out, Parser
from sem import output as sem_out, SemanticAnalyzer
from gen import output as gen_out, Generator

PHASES = {
    "lex": "Performs lexical analysis",
    "syn": "Performs syntactic analysis",
    "sem": "Performs semantic analysis",
    "gen": "Performs code generation",
    "exe": "Generates and executes the corresponding moon output file",
}


class PhaseHandler:
    def __init__(self, f, phase):
        self._file = f
        self._phase = phase
        self.success = True

        self.output = GenericOutput(f.name)

        self.lex = Scanner(f)
        self.fork = TokenForkWrapper(self.lex, self.output.token)
        self.syn = Parser(prodcution_handler=self.output, error_handler=self.output)
        self.sem = SemanticAnalyzer(output=self.output)
        self.gen = Generator()

    def run(self):
        getattr(self, "_" + self._phase, self._error)()
        if self._phase != "exe":
            self.output.finish(self._phase)

    def _error(self):
        raise Exception('Invalid phase "{}"'.format(self._phase))

    def _lex(self):
        for token in self.lex:
            self.output.token(token)

    def _syn(self):
        result = self.syn.start(self.fork)
        self.output.ast(result.ast)
        return result

    def _sem(self):
        result = self._syn()
        self.sem.start(result.ast)
        self.output.tables()
        return result

    def _gen(self):
        result = self._sem()
        if self.output.did_fail():
            return
        executable = self.gen.start(result.ast)
        self.output.executable(executable)

    def _exe(self):
        self._gen()
        self.output.finish(self._phase)
        if self.output.did_fail():
            return
        self.output.execute()


class TokenForkWrapper:
    def __init__(self, scanner, out):
        self.scanner = scanner
        self.out = out

    def __iter__(self):
        for token in self.scanner:
            self.out(token)
            yield token


class GenericOutput(lex_out.TokenOutput, syn_out.ParserOutput, sem_out.SemanticOutput):
    def __init__(self, source_file):
        super().__init__(source_file)
        self.source_file = source_file
        self.gen_out = gen_out.ExecutableOutput(self.source_file)

    def executable(self, exe: str):
        self.gen_out.write(exe)

    def _print_errors(self):
        errors = [e for e in lex_out.TokenOutput.list_errors(self)]
        errors += [
            (l, "Syntax " + e) for l, e in syn_out.ParserOutput.list_errors(self)
        ]
        errors += [
            (l, "Semantic " + e) for l, e in sem_out.SemanticOutput.list_errors(self)
        ]
        for _, error in sorted(errors):
            print(error[:-1])

        if errors:
            print()  # Padding

    def _print_status(self, phase):
        if lex_out.TokenOutput.did_fail(self):
            print(self.source_file + ": Invalid tokens found")
        elif phase == "lex":
            print(self.source_file + ": All tokens valid")
            return

        if syn_out.ParserOutput.did_fail(self):
            print(self.source_file + ": Failed to parse")
        elif phase == "syn":
            print(self.source_file + ": Parsed successfully")
            return

        if sem_out.SemanticOutput.did_fail(self):
            print(self.source_file + ": Failed to compile")
        elif sem_out.SemanticOutput.did_warn(self):
            print(self.source_file + ": Compiled with warnings")

        if self.did_fail():
            return

        print(self.source_file + ": Compiled successfully")

    def _collect_files(self, phase):
        files = lex_out.TokenOutput.collect_files(self)
        if phase == "lex":
            return files

        files += syn_out.ParserOutput.collect_files(self)
        if phase == "syn":
            return files

        files += sem_out.SemanticOutput.collect_files(self)
        if phase == "sem" or self.did_fail():
            return files

        return files + self.gen_out.collect_files()

    def _list_files(self, phase):
        files = self._collect_files(phase)
        print("Output found in:")
        for f in files:
            print("\t" + f)

    def finish(self, phase):
        self._print_errors()
        self._print_status(phase)
        self._list_files(phase)

    def did_fail(self):
        return (
            lex_out.TokenOutput.did_fail(self)
            or syn_out.ParserOutput.did_fail(self)
            or sem_out.SemanticOutput.did_fail(self)
        )

    def execute(self):
        import subprocess, os, sys

        f = self.gen_out.collect_files()[0]
        moon = os.environ.get("MOON", "./moon")

        print("\nStarting the moon simulator at: " + moon)
        print("-----------------------------------------------")
        subprocess.run(
            [moon, f, "moon_processor/samples/lib.m",],
            stderr=sys.stdout,
            stdout=sys.stdout,
            stdin=sys.stdin,
        )
