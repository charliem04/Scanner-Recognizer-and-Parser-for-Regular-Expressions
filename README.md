# Scanner and Recognizer for Regular Expressions

CMPS 450 — Project 1. A recursive descent **recognizer** for regular
expressions that prints a concrete syntax tree *without building one*.

A recognizer only decides whether its input is grammatical. It can still print
a parse tree, because the call graph of a recursive descent recognizer already
has the shape of that tree: each method prints its node name on entry and calls
its children one indentation level deeper, so the tree falls out of the control
flow. No tree data structure is ever allocated.

## Files

| File | What it holds |
| --- | --- |
| `regexTokenizer.py` | The scanner: `tokenize()` yields `Token(lexeme, type)` for the token types in Table 1 of the handout. Also carries a minimal `peekable` stand-in used only when `more_itertools` is missing. |
| `regexRecognizer.py` | `RegexParser`, one method per EBNF rewrite rule, plus `RegexSyntaxError`. |
| `main.py` | Driver. Processes the six sample expressions, or ones given on the command line. |
| `test_recognizer.py` | 18 unit tests, including a line-for-line comparison against the handout's output. |
| `expected_output.txt` | The parse trees printed in the handout, used as the golden file for that test. |

## Running it

```
python3 main.py
```

That prints the trees for the six expressions from the handout:
`two`, `t|w|o`, `[two]`, `[^two]`, `t(oo?|wo)`, and `(\<(/?[^\>]+)\>)`.

Expressions of your own can be passed as arguments:

```
python3 main.py 'a(b|c)*' '[0-9]+'
```

Tests:

```
python3 -m unittest -v test_recognizer.py
```

### Dependency

The handout specifies `more_itertools.peekable`:

```
pip install -r requirements.txt
```

`main.py` imports it exactly as the handout shows. If the library is not
installed, it falls back on the small `peekable` class in `regexTokenizer.py`,
which supports the same two operations the recognizer uses — `peek(None)` and
`next(...)`. Output is byte-for-byte identical either way, so the program runs
on a machine without the library.

## The grammar

EBNF, translated from the BNF in the handout. The left recursion in rules 1
and 2 becomes iteration, which is why the arguments of `|` and of
concatenation all come out as siblings at one level of the tree rather than
nested pairwise.

```
1. <re>            ::= <simple-re> { "|" <simple-re> }
2. <simple-re>     ::= <basic-re> { <basic-re> }
3. <basic-re>      ::= <elementary-re> [ "*" | "+" | "?" ]
4. <elementary-re> ::= "(" <re> ")" | "." | <char-or-meta>
                     | "[" <set-items> "]" | "[^" <set-items> "]"
5. <char-or-meta>  ::= any NON-METACHAR | any METACHAR except "\" | "\" METACHAR
6. <set-items>     ::= <char-or-meta> { <char-or-meta> }
```

Precedence, highest to lowest: parentheses, quantifiers, concatenation,
alternation. The three quantifiers `*`, `+`, and `?` are of equal precedence.

## How the tree is printed

Node names are `RE`, `S_RE`, `B_RE`, `E_RE`, `CHAR_OR_META`, and `SITEMS`,
for regular expression, simple, basic, and elementary regular expression, the
character-or-metacharacter rule, and a set-items list. Leaves print as
`lexeme` then token type, e.g. `t CHAR`. One indentation level is four spaces.

`parse_re(0)` starts at level 0; every call prints its node at the level it was
given and passes `level + 1` to its children. Terminals consumed by a rule are
children of that rule's node, so:

- `| VERT` prints at the same level as the `S_RE` nodes it separates — both
  are children of `RE`.
- A quantifier prints at the same level as the `E_RE` it applies to — both are
  children of `B_RE`.
- `( LPAREN`, the nested `RE`, and `) RPAREN` are all children of one `E_RE`.
- An escape such as `\<` is two tokens, `\ BSLASH` and `< LANGLE`, printed as
  two leaves under a single `CHAR_OR_META` node.

## Implementation notes

**Two-token lookahead.** The grammar needs it to tell `[` from `[^`. Rather
than unreading a character, the scanner resolves it: `[^` is scanned as one
`LNEGSET` token. The recognizer then never needs more than one token of
lookahead, and uses `peek` before every `next`, never calling `next` when
`peek` returns `None`.

**Where iteration stops.** `parse_simple_re` keeps consuming `<basic-re>`
while the next token is one that can start an `<elementary-re>`
(`ELEMENTARY_STARTERS` in `regexRecognizer.py`). Tokens that cannot — `|`,
`)`, `]`, a bare quantifier, or end of input — end the loop and hand control
back to the caller.

**Metacharacters inside a set.** Rule 5 admits any metacharacter except `\`,
so inside `[...]` the characters `|`, `(`, `.` and friends are ordinary set
items; only `]` closes the set and only `\` begins an escape.

**Errors.** A malformed expression raises `RegexSyntaxError` with a message
saying what was expected and what was found. `main.py` catches it, reports the
expression as bad, and carries on with the next one. `parse_re` stops at the
first token it cannot use, so the driver also calls `expect_end_of_input()` to
catch trailing garbage such as the `)` in `a)`. Rejected inputs include `(a`,
`a)`, `[ab`, `[]`, `*a`, `a**`, `|a`, `a|`, a trailing `\`, and any character
the scanner tokenizes as `ERROR`.

## Verification

`test_recognizer.py` compares the driver's full output, indentation included,
against `expected_output.txt`. That file's 133 lines were checked line for line
against the required output in the project handout. The remaining tests cover
the token types, the `peekable` fallback, the tree-shape rules listed above,
and the error cases.
