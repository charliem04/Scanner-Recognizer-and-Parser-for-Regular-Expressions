"""Driver for the regular expression recognizer.

CMPS 450 -- Project 1.

Run it with no arguments to process the six regular expressions from the
handout::

    python3 main.py

Or pass regular expressions of your own::

    python3 main.py 'a(b|c)*' '[0-9]+'
"""

import sys

import regexTokenizer as tk
from regexRecognizer import RegexParser, RegexSyntaxError

try:
    from more_itertools import peekable
except ImportError:  # fall back on the stand-in bundled with the scanner
    from regexTokenizer import peekable

#: The sample regular expressions given in the handout.
INPUTS = [
    'two',
    't|w|o',
    '[two]',
    '[^two]',
    't(oo?|wo)',
    "(\\<(/?[^\\>]+)\\>)",
]


def recognize(regex, out=None):
    """Print the concrete syntax tree of *regex*, or a syntax error message.

    Returns True when *regex* is grammatical.
    """
    stream = sys.stdout if out is None else out
    print(f'Processing expression: "{regex}"', file=stream)

    tokens = peekable(tk.tokenize(regex))
    parser = RegexParser(tokens, out=stream)
    try:
        parser.parse_re(0)
        parser.expect_end_of_input()
    except RegexSyntaxError as error:
        print(f"    ** syntax error: {error}", file=stream)
        return False
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    inputs = argv if argv else INPUTS

    ok = True
    for regex in inputs:
        ok = recognize(regex) and ok
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
