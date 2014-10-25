from __future__ import division

import sys
import readline
import operator

ERROR_FORMAT = ' ? %s %r'

class ForthException(Exception): pass

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
