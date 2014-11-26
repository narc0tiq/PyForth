# coding= utf-8
"""
Implements a Forth machine, i.e., an object capable of maintaining state and
responding to valid (and invalid) Forth code passed in from the command line in
a read-eval-print loop until explicitly told otherwise.

Usage should be as simple as:
    >>> import forth forth.Machine().loop()

Which should put you in the Forth REPL until given an end of file (^D on Linux)
or the BYE word.

The Forth machine may also be given strings to evaluate:
    >>> f = forth.Machine() f.eval("5 4 + .")
    "9  ok"

Wherein the return value is the response normally given by the Forth machine
(including the ' ok' representing end of successful evaluation of input).

The Forth machine is not particularly interested in being able to perform
curses-like treatment of the terminal as a grid of cells, therefore some words
(e.g. "PAGE") may do unexpected things (like just printing '\n' * 100
regardless of the terminal's actual size).
"""
from forth.machine import *
