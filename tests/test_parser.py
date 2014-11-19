import pytest
import forth


class TestTheParser():
    def test_empty_string(self):
        """ Parser refuses to parse past the end of the string. """
        p = forth.Parser('')

        with pytest.raises(StopIteration):
            p.parse_whitespace()

        with pytest.raises(StopIteration):
            p.parse_word()

        with pytest.raises(StopIteration):
            p.parse_newline()

        with pytest.raises(StopIteration):
            p.parse_rest_of_line()

        with pytest.raises(StopIteration):
            p.next_word()

    def test_all_whitespace(self):
        """ Parser consumes all whitespace in one gulp. """
        whitespace_string = "   \t\t  \t \t"
        p = forth.Parser(whitespace_string)

        assert p.parse_whitespace() == whitespace_string

        with pytest.raises(StopIteration):
            p.next_word()

        # Also, next_word will happily consume and ignore the whitespace itself.
        p = forth.Parser(whitespace_string)

        with pytest.raises(StopIteration):
            p.next_word()

    def test_single_word(self):
        """ A single word is returned immediately. """
        p = forth.Parser("JUST-ONE-WORD")

        assert p.next_word() == "JUST-ONE-WORD"

        # no further words exist
        with pytest.raises(StopIteration):
            p.next_word()

    def test_leading_whitespace(self):
        """ Leading whitespace is ignored. """
        p = forth.Parser("  \t HELLO-WORLD")

        assert p.next_word() == 'HELLO-WORLD'

        # no further words exist
        with pytest.raises(StopIteration):
            p.next_word()

    def test_more_words(self):
        """ Multiple words are returned one at a time. """
        p = forth.Parser("AND ON THE PEDESTAL,")

        assert p.next_word() == 'AND'
        assert p.next_word() == 'ON'
        assert p.next_word() == 'THE'
        assert p.next_word() == 'PEDESTAL,'

        with pytest.raises(StopIteration):
            p.next_word()

    def test_more_whitespace(self):
        """ All whitespace is eaten together and has no effect on words. """
        p = forth.Parser("   \tTHESE\t\tWORDS      APPEAR      \t  ")

        assert p.next_word() == 'THESE'
        assert p.next_word() == 'WORDS'
        assert p.next_word() == 'APPEAR'

        with pytest.raises(StopIteration):
            p.next_word()

    def test_newlines(self):
        """ Newlines are their own special word and will appear in the sequence. """
        p = forth.Parser("MY NAME IS OZYMANDIAS,\nKING OF KINGS!")

        assert p.next_word() == 'MY'
        assert p.next_word() == 'NAME'
        assert p.next_word() == 'IS'
        assert p.next_word() == 'OZYMANDIAS,'
        assert p.next_word() == '\n'
        assert p.next_word() == 'KING'
        assert p.next_word() == 'OF'
        assert p.next_word() == 'KINGS!'

        with pytest.raises(StopIteration):
            p.next_word()

