"""Recursive descent recognizer for regular expressions.

CMPS 450 -- Project 1.

A recognizer only decides whether its input is grammatical; it does not build
a parse tree.  It can nevertheless *print* one, because the call graph of a
recursive descent recognizer has exactly the shape of the concrete syntax
tree.  Each method below prints its node name on entry and then calls the
methods for its children one indentation level deeper, so the tree falls out
of the control flow.

The methods follow the EBNF of the handout one for one:

    1. <re>            ::= <simple-re> { "|" <simple-re> }
    2. <simple-re>     ::= <basic-re> { <basic-re> }
    3. <basic-re>      ::= <elementary-re> [ "*" | "+" | "?" ]
    4. <elementary-re> ::= "(" <re> ")" | "." | <char-or-meta>
                         | "[" <set-items> "]" | "[^" <set-items> "]"
    5. <char-or-meta>  ::= any NON-METACHAR | any METACHAR except "\\"
                         | "\\" METACHAR
    6. <set-items>     ::= <char-or-meta> { <char-or-meta> }

Precedence runs, highest to lowest: parentheses, quantifiers, concatenation,
alternation.  Rules 1 and 2 are left recursive in the BNF; the EBNF replaces
that recursion with iteration, which is why the arguments of ``|`` and of
concatenation all come out as siblings at the same level of the tree.
"""

import sys

#: Number of spaces that one level of indentation is worth.
INDENT = "    "

#: Token types that can begin an <elementary-re>, and therefore a <basic-re>.
#: This is the set the iteration in <re> and <simple-re> tests against.
ELEMENTARY_STARTERS = frozenset(
    {"LPAREN", "PERIOD", "LPOSSET", "LNEGSET", "BSLASH", "CHAR", "LANGLE", "RANGLE"}
)

#: The three quantifiers, which are of equal precedence.
QUANTIFIERS = frozenset({"STAR", "PLUS", "QMARK"})

#: Token types that end a <set-items> list.
SET_TERMINATORS = frozenset({"RSET", "EOL"})


class RegexSyntaxError(Exception):
    """Raised when the token stream is not a sentence of the grammar."""


class RegexParser:
    """Recognizes a regular expression and prints its concrete syntax tree.

    *tokens* is a peekable stream of tokens, as produced by
    ``peekable(regexTokenizer.tokenize(regex))``.  A parser instance consumes
    its stream once, so build a new one per regular expression::

        tokens = peekable(tk.tokenize(regex))
        parser = RegexParser(tokens)
        parser.parse_re(0)
        parser.expect_end_of_input()

    Output goes to *out* (standard output by default), which makes the parse
    trees easy to capture in tests.
    """

    def __init__(self, tokens, out=None):
        self.tokens = tokens
        self.out = sys.stdout if out is None else out

    # ----------------------------------------------------------------- #
    # Token stream helpers
    # ----------------------------------------------------------------- #

    def peek(self):
        """Return the next token without consuming it, or None at end of input."""
        return self.tokens.peek(None)

    def peek_type(self):
        """Return the type of the next token, or None at end of input."""
        token = self.peek()
        return None if token is None else token[1]

    def _advance(self, level):
        """Consume the next token and print it as a leaf at *level*."""
        token = next(self.tokens)
        self._emit(level, f"{token[0]} {token[1]}")
        return token

    def _expect(self, token_type, level, expected):
        """Consume and print the next token, which must be of *token_type*."""
        token = self.peek()
        if token is None:
            raise RegexSyntaxError(f"expected {expected} but reached end of input")
        if token[1] != token_type:
            raise RegexSyntaxError(f"expected {expected} but found '{token[0]}' ({token[1]})")
        return self._advance(level)

    def expect_end_of_input(self):
        """Check that the whole token stream was consumed.

        ``parse_re`` stops at the first token it cannot use, so a stray ``)``
        or quantifier would otherwise be silently ignored.
        """
        token = self.peek()
        if token is not None:
            raise RegexSyntaxError(f"unexpected trailing input at '{token[0]}' ({token[1]})")

    # ----------------------------------------------------------------- #
    # Printing helpers
    # ----------------------------------------------------------------- #

    def _emit(self, level, text):
        """Print one node of the tree, indented to *level*."""
        print(f"{INDENT * level}{text}", file=self.out)

    # ----------------------------------------------------------------- #
    # One method per EBNF rewrite rule
    # ----------------------------------------------------------------- #

    def parse_re(self, level=0):
        """<re> ::= <simple-re> { "|" <simple-re> }"""
        self._emit(level, "RE")
        self.parse_simple_re(level + 1)
        # Every alternative, and every "|" between them, is a child of this
        # node, so they all print at the same level.
        while self.peek_type() == "VERT":
            self._advance(level + 1)
            self.parse_simple_re(level + 1)

    def parse_simple_re(self, level):
        """<simple-re> ::= <basic-re> { <basic-re> }"""
        self._emit(level, "S_RE")
        self.parse_basic_re(level + 1)
        while self.peek_type() in ELEMENTARY_STARTERS:
            self.parse_basic_re(level + 1)

    def parse_basic_re(self, level):
        """<basic-re> ::= <elementary-re> [ "*" | "+" | "?" ]"""
        self._emit(level, "B_RE")
        self.parse_elementary_re(level + 1)
        if self.peek_type() in QUANTIFIERS:
            self._advance(level + 1)

    def parse_elementary_re(self, level):
        """<elementary-re> ::= "(" <re> ")" | "." | <char-or-meta>
        | "[" <set-items> "]" | "[^" <set-items> "]"
        """
        self._emit(level, "E_RE")
        token = self.peek()
        if token is None:
            raise RegexSyntaxError("expected an expression but reached end of input")

        token_type = token[1]
        if token_type == "LPAREN":
            self._advance(level + 1)
            self.parse_re(level + 1)
            self._expect("RPAREN", level + 1, "')'")
        elif token_type == "PERIOD":
            self._advance(level + 1)
        elif token_type in ("LPOSSET", "LNEGSET"):
            self._advance(level + 1)
            self.parse_set_items(level + 1)
            self._expect("RSET", level + 1, "']'")
        elif token_type in ELEMENTARY_STARTERS:
            self.parse_char_or_meta(level + 1)
        else:
            raise RegexSyntaxError(
                f"'{token[0]}' ({token_type}) cannot start an expression"
            )

    def parse_char_or_meta(self, level):
        """<char-or-meta> ::= any NON-METACHAR | any METACHAR except "\\"
        | "\\" METACHAR

        An escape is two tokens -- the backslash and the character it escapes
        -- and both print as children of the same CHAR_OR_META node.
        """
        self._emit(level, "CHAR_OR_META")
        token = self.peek()
        if token is None:
            raise RegexSyntaxError("expected a character but reached end of input")
        if token[1] == "ERROR":
            raise RegexSyntaxError(f"unrecognized character {token[0]!r}")

        if token[1] == "BSLASH":
            self._advance(level + 1)
            escaped = self.peek()
            if escaped is None:
                raise RegexSyntaxError("'\\' at end of input has nothing to escape")
            if escaped[1] == "ERROR":
                raise RegexSyntaxError(f"unrecognized character {escaped[0]!r} after '\\'")
            self._advance(level + 1)
        else:
            self._advance(level + 1)

    def parse_set_items(self, level):
        """<set-items> ::= <char-or-meta> { <char-or-meta> }

        Inside a set the metacharacters lose their special meaning, so every
        token up to the closing ']' is taken as a <char-or-meta>.
        """
        self._emit(level, "SITEMS")
        if self.peek() is None or self.peek_type() in SET_TERMINATORS:
            raise RegexSyntaxError("a set must contain at least one character")
        self.parse_char_or_meta(level + 1)
        while self.peek() is not None and self.peek_type() not in SET_TERMINATORS:
            self.parse_char_or_meta(level + 1)
