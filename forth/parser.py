import re


class Parser(object):
    """
    Very simple Forth parser -- not much more than a few primitives useful for
    consuming an input string in a Forth-compatible way (e.g. consume a word,
    consume to end of line).

    The parser is stateful, in as much as each instance thereof is given an
    initial string to operate on, and calls to parse_whatever will advance the
    parser's position within that string, if necessary (thus, the next call
    will start from where the previous left off).

    The parser is not a compiler nor an interpreter: its purpose in life is to
    take strings and allow a compiler or interpreter to tokenize them in
    whichever way feels most normal.  Therefore, the parser output is not a
    parse tree: the Forth machine may choose to change its parsing rules
    mid-string, and this must be supported.

    As an example, `Parser(": STAR 42 EMIT ;")` cannot interpret its contents
    in any meaningful way: the ":" and ";" words trigger immediate changes in
    the Forth machine's mode of operation (taking it from IMMEDIATE to COMPILE
    mode and back, respectively).

    The parse_* methods will usually raise :exc:`StopIteration` when the string
    has been completely consumed; at that point, the current :class:`Parser`
    instance may be thrown away and a fresh one made for the next bits of
    input.

    The expected external interface is provided by the next_word method, which
    will happily return the next word or newline, consuming them as well as any
    preceding spaces, until the string is completely empty, at which point
    :exc:`StopIteration` will be raised.
    """
    def __init__(self, text):
        self.text = text
        self.pos = 0

    @property
    def is_finished(self):
        return self.pos >= len(self.text)

    def _consume(self, pattern):
        """
        Consume (advancing self.pos) some characters based on a regex. The
        regex is applied to a slice of self.text starting from self.pos and
        ending at the end of the string.

        Note that matches are only ever expected at the start of the string
        slice.
        """
        if self.is_finished:
            raise StopIteration()
        found = re.match(pattern, self.text[self.pos:])
        if found is None:
            return None
        self.pos += found.end()
        return found.group()


    def parse_whitespace(self):
        return self._consume(r'[ \t\n]*')

    def parse_word(self):
        return self._consume(r'[^ \t\n]+')

    def parse_rest_of_line(self):
        return self._consume(r'[^\n]*')

    def next_word(self):
        self.parse_whitespace()
        return self.parse_word()

    def generate(self):
        while True:
            yield self.next_word()

