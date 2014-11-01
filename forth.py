from __future__ import division

import sys
import readline
import operator
import string

ERROR_FORMAT = ' ? %s %r'

class ForthException(Exception): pass
class BadNumberSyntax(ForthException): pass
class UnknownWord(ForthException): pass
class UnknownToken(ForthException): pass
class EmptyStack(ForthException): pass
class InsufficientValues(ForthException): pass
class StringMathIsBadAndYouShouldFeelBad(ForthException): pass
class BadParserEndState(ForthException): pass


def BadEndState(message):
    def BadEndStateDecorator(decorated):
        decorated.bad_end_state = message
        return decorated
    return BadEndStateDecorator


class Lexer(object):
    """
    A forth.Lexer will return tokens (which are tuples (type, value)) representing
    lexically-important parts of the input (presumably Forth) text.

    Example:
        >>> lex = forth.Lexer('2 3 * .')
        >>> print lex.tokens()
    """
    def __init__(self, text):
        self.text = text
        self._tokens = []  # Our current batch of tokens. Often empty.

    def tokens(self):
        """
        Generator yielding the tokens in the input text.

        This also drives the lexing process in the first place, by triggering a scan
        for more lexemes if none are immediately available.

        Lexical errors will be raised as ForthException()s.
        """
        self._state = self._lexWhitespace  # The next state method we'll run
        self._start = 0  # The start of the current token.
        self._pos = 0  # Our position in the text being lexed.

        while True:
            if self._tokens:
                yield self._tokens.pop()
            else:
                self._tokenize()

    def _tokenize(self):
        """
        Perform the next state in the state machine. Raises StopIteration if there
        isn't one (for convenience in a generator context).
        """
        if self._state is not None:
            self._state = self._state()
        else:  # No next state means we're done parsing this text.
            raise StopIteration()

    def _peek(self):
        """ Previews the next character of input (but does not consume it). """
        if self._pos >= len(self.text):
            return None
        char = self.text[self._pos]
        return char

    def _next(self):
        """ Consumes and returns the next character of input. """
        char = self._peek()
        self._pos += 1
        return char

    def _undo(self):
        """
        Undoes a single self._next, effectively un-consuming it.
        After the end of the string has been consumed, undo is no longer possible.
        """
        if self._pos < len(self.text):
            self._pos -= 1

    def _accept(self, allowed_chars):
        """ Accept the next character _if_ it's within the given set of allowed_chars. """
        char = self._next()
        if char is None:
            return False # never accept past the end of the string
        elif char in allowed_chars:
            return True
        else:
            self._undo()
            return False

    def _accept_run(self, allowed_chars):
        """ Accept characters until one comes up that's not in the allowed_chars. """
        while self._accept(allowed_chars):
            pass  # a little magic, but really nothing to do here.

    @property
    def _pending_text(self):
        return self.text[self._start:self._pos]

    def _emit_unless_empty(self, token_type):
        """ Emit a token only if the current pending text is not empty. """
        if self._pending_text:
            self._emit(token_type)

    def _emit(self, token_type):
        """ Emit a token consisting of the currently pending text (start to pos). """
        self._tokens.insert(0, (token_type, self._pending_text))
        self._start = self._pos

    def _ignore(self):
        """ Dismiss the currently pending text and start a new token. """
        self._start = self._pos

    def _lexWhitespace(self):
        char = self._next()

        # Consume character until either a non-whitespace or the end of string
        while char is not None and char.isspace():
            char = self._next()

        # Unconsume that last character so we can dispatch correctly.
        self._undo()  # note: does not undo an end-of-string
        self._emit_unless_empty('whitespace')

        if char is None:
            self._emit('eof')
            return None  # No further states
        elif char in '+-0123456789':
            return self._lex_number
        elif char == '"':
            return self._lex_quoted_string
        else:
            return self._lex_word

    def _lex_number(self):
        self._accept("+-") # optional leading sign
        # 123.456 is okay
        self._accept_run(string.digits)
        if self._accept("."):
            self._accept_run(string.digits)

        # 123xyz is not okay
        char = self._peek()
        if char is not None and char.isalpha():
            self._next()
            raise BadNumberSyntax(self._pending_text, "Unexpected trailing alphabetic character")

        self._emit("number")
        return self._lexWhitespace

    def _lex_word(self):
        self._accept_run(string.letters + string.digits)
        self._emit_unless_empty('word')
        return self._lexWhitespace

    def _lex_quoted_string(self):
        self._accept('"')
        self._ignore()
        char = self._next()
        while char is not None and char != '"':
            char = self._next()
        self._undo()
        self._emit_unless_empty('string')
        self._accept('"')
        self._ignore()
        return self._lexWhitespace


class ForthParser(object):
    def _parse_number_or_word(self, word):
        try:
            number = float(word)
            self.tokens.append(('number', number))
            return self._parse_number_or_word
        except ValueError:
            pass

        if word == '"':
            return self._parse_string
        elif word == '(':
            return self._parse_comment
        elif word == '#':
            return self._parse_eol_comment
        else:
            self.tokens.append(('word', word))
            return self._parse_number_or_word

    @BadEndState('Unterminated comment.')
    def _parse_comment(self, word):
        if word and word[-1] == ')':
            return self._parse_number_or_word
        return self._parse_comment

    def _parse_eol_comment(self, word):
        return self._parse_eol_comment

    @BadEndState('Unterminated string.')
    def _parse_string(self, word):
        self.string += word

        if word and word[-1] == '"':
            self.tokens.append(('string', self.string[:-1]))
            self.string = ''
            return self._parse_number_or_word
        else:
            self.string += ' '
            return self._parse_string

    def parse(self, text):
        self.tokens = []
        self.string = ''
        parse_with = self._parse_number_or_word

        words = text.split(' ')
        for word in words:
            parse_with = parse_with(word)

        if hasattr(parse_with, 'bad_end_state'):
            raise BadParserEndState(parse_with.bad_end_state)

        return self.tokens


class ForthMachine(object):
    def __init__(self):
        self.parser = ForthParser()
        self.data_stack = []
        self.return_stack = []
        self.token_methods = {
            'number': self._push_to_data,
            'string': self._push_to_data,
            'word': self._eval,
        }

        self.word_methods = {
            '.S': self._print_stack,
            '.': self._print_and_pop,
            '+': self._two_operand_math(operator.add),
            '-': self._two_operand_math(operator.sub),
            '*': self._two_operand_math(operator.mul),
            '/': self._two_operand_math(operator.div),
            '0SP': self._clear_stack,
            'DUP': self._dupe_top_of_stack,
            'SWAP': self._swap_top_of_stack,
            'DROP': self._drop_top_of_stack,
            '<': self._two_operand_math(operator.lt),
            '<=': self._two_operand_math(operator.le),
            '>': self._two_operand_math(operator.gt),
            '>=': self._two_operand_math(operator.ge),
            '==': self._two_operand_math(operator.eq),
            '!=': self._two_operand_math(operator.ne),
            'IF': self._if,
            'ELSE': self._else,
            'THEN': self._then,
        }

    def _if(self):
        if not self.data_stack:
            raise InsufficientValues(1, self.data_stack)
        self.return_stack.append(bool(self.data_stack.pop()))
        return ''

    def _else(self):
        if not self.return_stack:
            raise InsufficientReturnValues(1, self.return_stack)
        self.return_stack.append(not self.return_stack.pop())
        return ''

    def _then(self):
        if not self.return_stack:
            raise InsufficientReturnValues(1, self.return_stack)
        self.return_stack.pop()
        return ''

    def eval(self, text):
        output = ''
        try:
            tokens = self.parser.parse(text)
            for token in tokens:
                if token[0] in self.token_methods:
                    if self.return_stack:
                        if self.return_stack[-1] or token[1] == 'ELSE' or token[1] == 'THEN':
                            output += self.token_methods[token[0]](token[1])
                    else:
                        output += self.token_methods[token[0]](token[1])
                else:
                    raise UnknownToken(token[1])
        except ForthException as ex:
            return ERROR_FORMAT % (output, ex)
        return 'OK ' + output

    def _push_to_data(self, data):
        self.data_stack.append(data)
        return ''

    def _eval(self, word):
        if word in self.word_methods:
            return ' ' + self.word_methods[word]()
        else:
            raise UnknownWord(word)

    def _print_stack(self):
        return ' '.join(map(repr,self.data_stack))

    def _print_and_pop(self):
        if self.data_stack:
            return str(self.data_stack.pop())
        raise EmptyStack()

    def _two_operand_math(self, operation):
        def closure():
            if len(self.data_stack) < 2:
                raise InsufficientValues(2, self.data_stack)
            right = self.data_stack.pop()
            left = self.data_stack.pop()
            try:
                self.data_stack.append(operation(left, right))
            except TypeError:
                raise StringMathIsBadAndYouShouldFeelBad(left, right)
            return ''
        return closure

    def _clear_stack(self):
        del self.data_stack[:]
        return ''

    def _dupe_top_of_stack(self):
        if not self.data_stack:
            raise InsufficientValues(1, self.data_stack)
        self.data_stack.append(self.data_stack[-1])
        return ''

    def _swap_top_of_stack(self):
        if len(self.data_stack) < 2:
            raise InsufficientValues(2, self.data_stack)
        last = self.data_stack.pop()
        previous = self.data_stack.pop()
        self.data_stack.extend((last, previous))
        return ''

    def _drop_top_of_stack(self):
        if not self.data_stack:
            raise InsufficientValues(1, self.data_stack)
        self.data_stack.pop()
        return ''


def read_eval_print_loop():
    try:
        forth = ForthMachine()

        while True:
            line = raw_input('> ')
            result = forth.eval(line)
            print result
    except EOFError:
        return 0


if __name__ == '__main__':
    sys.exit(read_eval_print_loop())
