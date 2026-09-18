"""Scanner (tokenizer) for regular expressions.

Charles Meyers
CMPS 450 -- Professor Maida
Project 1: Implementing a Scanner, Recognizer, and Parser for Regular Expressions
Due: October 14, 2026

The scanner turns a regular expression (a plain Python string) into a stream
of ``Token`` objects.  The token types are the ones given in Table 1 of the
project handout:

    ======  ==========      ======  ==========
    "|"     VERT            "]"     RSET
    "*"     STAR            "<"     LANGLE
    "+"     PLUS            ">"     RANGLE
    "?"     QMARK           "\\"     BSLASH
    "("     LPAREN          "\\n"    EOL
    ")"     RPAREN          A-Za-z_ CHAR
    "."     PERIOD          other   ERROR
    "[^"    LNEGSET
    "["     LPOSSET
    ======  ==========      ======  ==========

``tokenize`` is a generator, so it is meant to be wrapped in
``more_itertools.peekable`` before being handed to the recognizer::

    import regexTokenizer as tk
    from more_itertools import peekable

    tokens = peekable(tk.tokenize('t(oo?|wo)'))
"""

from collections import namedtuple


class Token(namedtuple("Token", ["lexeme", "type"])):
    """A single token: the text that was matched plus its token type.

    ``Token`` is a ``namedtuple``, so a token can be used either by name
    (``tok.lexeme``, ``tok.type``) or by position (``tok[0]``, ``tok[1]``).
    Printing a token gives the form the recognizer needs for its parse
    trees, e.g. ``t CHAR``.
    """

    __slots__ = ()

    def __str__(self):
        return f"{self.lexeme} {self.type}"


#: Single-character metacharacters and the token type each one produces.
METACHARS = {
    "|": "VERT",
    "*": "STAR",
    "+": "PLUS",
    "?": "QMARK",
    "(": "LPAREN",
    ")": "RPAREN",
    ".": "PERIOD",
    "[": "LPOSSET",
    "]": "RSET",
    "<": "LANGLE",
    ">": "RANGLE",
    "\\": "BSLASH",
    "\n": "EOL",
}

#: The one two-character token in the grammar.
NEGSET_LEXEME = "[^"


def tokenize(text):
    """Yield a :class:`Token` for every token in *text*.

    ``"[^"`` is scanned as the single token ``LNEGSET``; a ``"["`` that is
    not followed by ``"^"`` is ``LPOSSET``.  Any printable character that is
    not a metacharacter is a ``CHAR``; anything else (a control character,
    say) is an ``ERROR`` token, which the recognizer rejects.
    """
    i = 0
    n = len(text)
    while i < n:
        c = text[i]

        # "[^" is two characters but only one token, so it is tested first.
        if c == "[" and text.startswith(NEGSET_LEXEME, i):
            yield Token(NEGSET_LEXEME, "LNEGSET")
            i += 2
        elif c in METACHARS:
            yield Token(c, METACHARS[c])
            i += 1
        elif c.isprintable():
            yield Token(c, "CHAR")
            i += 1
        else:
            yield Token(c, "ERROR")
            i += 1


class peekable:
    """Minimal stand-in for ``more_itertools.peekable``.

    The project is written against ``more_itertools``; this class exists only
    so the program still runs where that library is not installed.  It
    supports the two operations the recognizer uses: ``peek(default)`` to look
    at the next token without consuming it, and ``next(...)`` to consume one.
    """

    _SENTINEL = object()

    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._cache = []

    def __iter__(self):
        return self

    def __next__(self):
        if self._cache:
            return self._cache.pop(0)
        return next(self._iterator)

    def __bool__(self):
        return self.peek(self._SENTINEL) is not self._SENTINEL

    def peek(self, default=_SENTINEL):
        """Return the next item without consuming it."""
        if not self._cache:
            try:
                self._cache.append(next(self._iterator))
            except StopIteration:
                if default is self._SENTINEL:
                    raise
                return default
        return self._cache[0]
