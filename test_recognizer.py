"""Tests for the regular expression scanner and recognizer.

Charles Meyers
CMPS 450 -- Professor Maida
Project 1: Implementing a Scanner, Recognizer, and Parser for Regular Expressions
Due: October 14, 2026

Run with::

    python3 -m unittest -v test_recognizer.py

The main test compares the program's output against ``expected_output.txt``,
which holds the parse trees printed in the project handout.
"""

import io
import os
import unittest

import main
import regexTokenizer as tk
from regexRecognizer import RegexParser, RegexSyntaxError
from regexTokenizer import peekable

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED = os.path.join(HERE, "expected_output.txt")


def parse_tree(regex):
    """Return the parse tree the recognizer prints for *regex*."""
    out = io.StringIO()
    parser = RegexParser(peekable(tk.tokenize(regex)), out=out)
    parser.parse_re(0)
    parser.expect_end_of_input()
    return out.getvalue()


class TestScanner(unittest.TestCase):
    def test_token_types(self):
        tokens = [tuple(t) for t in tk.tokenize("a|b*c+d?(e).[f][^g]<h>\\")]
        self.assertEqual(
            tokens,
            [
                ("a", "CHAR"), ("|", "VERT"), ("b", "CHAR"), ("*", "STAR"),
                ("c", "CHAR"), ("+", "PLUS"), ("d", "CHAR"), ("?", "QMARK"),
                ("(", "LPAREN"), ("e", "CHAR"), (")", "RPAREN"), (".", "PERIOD"),
                ("[", "LPOSSET"), ("f", "CHAR"), ("]", "RSET"),
                ("[^", "LNEGSET"), ("g", "CHAR"), ("]", "RSET"),
                ("<", "LANGLE"), ("h", "CHAR"), (">", "RANGLE"),
                ("\\", "BSLASH"),
            ],
        )

    def test_negated_set_is_one_token(self):
        self.assertEqual(list(tk.tokenize("[^"))[0], ("[^", "LNEGSET"))

    def test_bare_bracket_is_positive_set(self):
        self.assertEqual(list(tk.tokenize("["))[0], ("[", "LPOSSET"))

    def test_newline_is_eol(self):
        self.assertEqual(list(tk.tokenize("\n"))[0], ("\n", "EOL"))

    def test_unrecognized_character_is_error(self):
        self.assertEqual(list(tk.tokenize("\t"))[0], ("\t", "ERROR"))

    def test_token_prints_lexeme_and_type(self):
        self.assertEqual(str(tk.Token("t", "CHAR")), "t CHAR")


class TestPeekableFallback(unittest.TestCase):
    def test_peek_does_not_advance(self):
        stream = peekable(iter([1, 2, 3]))
        self.assertEqual(stream.peek(None), 1)
        self.assertEqual(stream.peek(None), 1)
        self.assertEqual(next(stream), 1)
        self.assertEqual(next(stream), 2)

    def test_peek_returns_sentinel_at_end(self):
        stream = peekable(iter([]))
        self.assertIsNone(stream.peek(None))


class TestHandoutOutput(unittest.TestCase):
    def test_matches_expected_output(self):
        with open(EXPECTED, encoding="utf-8") as handle:
            expected = handle.read()
        out = io.StringIO()
        for regex in main.INPUTS:
            main.recognize(regex, out=out)
            print(file=out)
        self.assertEqual(out.getvalue(), expected)

    def test_every_handout_input_is_grammatical(self):
        for regex in main.INPUTS:
            with self.subTest(regex=regex):
                self.assertTrue(main.recognize(regex, out=io.StringIO()))


class TestTreeShape(unittest.TestCase):
    def test_concatenation_siblings_share_a_level(self):
        # "two" is three <basic-re> children of one <simple-re>.
        self.assertEqual(
            parse_tree("two"),
            "RE\n"
            "    S_RE\n"
            "        B_RE\n"
            "            E_RE\n"
            "                CHAR_OR_META\n"
            "                    t CHAR\n"
            "        B_RE\n"
            "            E_RE\n"
            "                CHAR_OR_META\n"
            "                    w CHAR\n"
            "        B_RE\n"
            "            E_RE\n"
            "                CHAR_OR_META\n"
            "                    o CHAR\n",
        )

    def test_quantifier_is_a_child_of_basic_re(self):
        lines = parse_tree("a*").splitlines()
        self.assertEqual(lines[-2].strip(), "a CHAR")
        self.assertEqual(lines[-1], "            * STAR")

    def test_period_is_an_elementary_re_not_a_char(self):
        self.assertNotIn("CHAR_OR_META", parse_tree("."))
        self.assertIn("            . PERIOD", parse_tree("."))

    def test_escape_prints_two_leaves_under_one_node(self):
        lines = [line.strip() for line in parse_tree("\\<").splitlines()]
        self.assertEqual(lines[-3:], ["CHAR_OR_META", "\\ BSLASH", "< LANGLE"])

    def test_metacharacters_lose_their_meaning_inside_a_set(self):
        # '|' and '(' inside a set are ordinary <char-or-meta> items.
        lines = [line.strip() for line in parse_tree("[|(]").splitlines()]
        self.assertIn("| VERT", lines)
        self.assertIn("( LPAREN", lines)
        self.assertEqual(lines[-1], "] RSET")

    def test_nested_groups(self):
        # One <re> node for the whole expression and one per parenthesized group.
        lines = [line.strip() for line in parse_tree("((a))").splitlines()]
        self.assertEqual(lines.count("RE"), 3)
        self.assertEqual(lines.count("( LPAREN"), 2)
        self.assertEqual(lines.count(") RPAREN"), 2)


class TestSyntaxErrors(unittest.TestCase):
    def assertRejects(self, regex):
        with self.subTest(regex=regex):
            with self.assertRaises(RegexSyntaxError):
                parse_tree(regex)

    def test_rejects_malformed_expressions(self):
        for regex in [
            "",            # empty input
            "(a",          # unclosed group
            "a)",          # unopened group
            "[ab",         # unclosed set
            "*a",          # quantifier with nothing to quantify
            "a**",         # quantifier applied to a quantifier
            "|a",          # alternation with an empty left branch
            "a|",          # alternation with an empty right branch
            "\\",          # backslash with nothing to escape
            "[]",          # empty set
            "a\tb",        # unrecognized character
        ]:
            self.assertRejects(regex)

    def test_driver_reports_errors_without_crashing(self):
        out = io.StringIO()
        self.assertFalse(main.recognize("(a", out=out))
        self.assertIn("syntax error", out.getvalue())


if __name__ == "__main__":
    unittest.main()
