def __ord_set(start, end):
    """Set of characters with contiguous Unicode values between `start` and `end`"""
    return set(chr(i) for i in range(ord(start), ord(end) + 1))


WHITESPACE = {" ", "\t", "\n", "\r"}
LOWER = __ord_set("a", "z")
UPPER = __ord_set("A", "Z")
LETTER = LOWER.union(UPPER)
NON_ZERO = __ord_set("1", "9")
DIGIT = NON_ZERO.union(set("0"))
ALPHANUM = LETTER.union(DIGIT).union(set("_"))
SINGLE_SYMBOL = {"+", "-", "*", ";", ".", ",", "(", ")", "{", "}", "[", "]"}
DUAL_SYMBOL = {"=", "<", ">", "/", ":"}
SYMBOL = SINGLE_SYMBOL.union(DUAL_SYMBOL)
