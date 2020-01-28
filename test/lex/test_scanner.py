from collections import defaultdict
from unittest import TestCase

from lex import Scanner

from .fixtures import SAMPLE


class ScannerTestCase(TestCase):
    def __extract_tokens(self, scanner):
        result = defaultdict(list)
        for token in scanner:
            result[token.location].append(token)

        return result

    def test_full_scan(self):
        scanner = Scanner(SAMPLE.input)
        result = self.__extract_tokens(scanner)

        for line in SAMPLE.expected.keys():
            self.assertListEqual(SAMPLE.expected[line], result[line])

        self.assertListEqual(list(SAMPLE.expected.keys()), list(result.keys()))
