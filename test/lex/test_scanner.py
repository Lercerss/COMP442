from collections import defaultdict
from unittest import TestCase

from lex import Scanner

from .fixtures import SAMPLE, SINGLE_INLINE_CMT


class ScannerTestCase(TestCase):
    def _extract_tokens(self, scanner):
        result = defaultdict(list)
        for token in scanner:
            result[token.location.line].append(token)

        return result

    def _full_scan(self, sample):
        scanner = Scanner(sample.input)
        result = self._extract_tokens(scanner)

        for line in sample.expected.keys():
            self.assertListEqual(sample.expected[line], result[line])

        self.assertListEqual(list(sample.expected.keys()), list(result.keys()))

    def test_full_scan(self):
        self._full_scan(SAMPLE)

    def test_single_inline_cmt(self):
        self._full_scan(SINGLE_INLINE_CMT)
