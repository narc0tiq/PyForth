# coding= utf-8
from __future__ import unicode_literals

from forth.parser import Parser

import inspect
import types

class ForthError(Exception): pass

IMMEDIATE_MODE = 9900
COMPILE_MODE = 9901

def _word(name=None):
    """
    Creates a decorator that adds a .word member to its given func, which may
    then be inspected for by the :class:`Machine`'s __init__ method. Note that
    if you already have an instance of :class:`Machine`, it's too late to
    decorate and you should call its :method:`Machine._add_stackmethod`
    instead.
    """
    def decorator(func):
        if name is None:
            func.word = func.func_name.upper()
        else:
            func.word = name
        return func
    return decorator

def _compile_word(meth):
    """
    Provides some automatic behaviour for @_words which are compile-only words
    -- namely, gives them a default handler that checks if their instance of
    :class:`Machine` is in compile mode, and raises ForthError if not.
    """
    def decorated(self):
        if self.mode is not COMPILE_MODE:
            raise ForthError('compile-only word')
        return meth(self)
    decorated.is_compile_word = True
    return decorated


class Machine(object):
    """ A Forth machine. It has stacks and registers and things. """
    def __init__(self):
        self.data_stack = []
        self.parser = None
        self.words = {}
        self.mode = IMMEDIATE_MODE
        self.now_compiling = None
        self.compile_queue = []

        # Add decorated member words
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, 'word'):
                self.words[method.word] = method

        # Add basic math and stack handling
        self.add_stackmethod('+', lambda b, a: a + b)
        self.add_stackmethod('-', lambda b, a: a - b)
        self.add_stackmethod('*', lambda b, a: a * b)
        self.add_stackmethod('/', lambda b, a: a / b)
        self.add_stackmethod('MOD', lambda b, a: a % b)
        self.add_stackmethod('/MOD', lambda b, a: reversed(divmod(a, b)))
        self.add_stackmethod('SWAP', lambda b, a: (b, a))
        self.add_stackmethod('DUP', lambda a: (a, a))
        self.add_stackmethod('OVER', lambda b, a: (a, b, a))
        self.add_stackmethod('ROT', lambda c, b, a: (b, c, a))
        self.add_stackmethod('DROP', lambda a: None)
        self.add_stackmethod('TUCK', lambda b, a: (b, a, b))

    def _pop(self):
        if self.data_stack:
            return self.data_stack.pop()
        else:
            raise ForthError('stack underflow')

    @_word('.')
    def _stack_pop(self):
        return str(self._pop()) + ' '

    @_word('.S')
    def _print_stack(self):
        return repr(self.data_stack) + ' '

    @_word()
    def emit(self):
        value = self._pop()
        return unichr(value)

    @_word(':')
    def begin_compile(self):
        try:
            new_word = self.parser.next_word()
        except StopIteration:
            raise ForthError('no name given')

        self.mode = COMPILE_MODE
        self.now_compiling = new_word
        self.compile_queue = []

    @_word(';')
    @_compile_word
    def end_compile(self):
        tokens = self.compile_queue
        new_word = lambda self: self.interpret(tokens)
        self.words[self.now_compiling] = types.MethodType(new_word, self)

        self.mode = IMMEDIATE_MODE
        self.now_compiling = None
        self.compile_queue = []

    @_word('COMPILE_WORD_WITH_OUTPUT_FOR_TESTING')
    @_compile_word
    def test_compiler_output(self):
        return 'SOME OUTPUT!!!'

    def add_stackmethod(self, word, func):
        """
        Turns a given function `func` into a stack-consumer.

        The function will get its arguments from the stack automatically, in
        the order they pop off (so from the stack [1, 2] the call to a
        two-argument function will be func(2, 1). The function's return value
        (or values) are assumed to go back on the stack.

        There is no provision for a stack-consumer to yield any output text,
        nor for it to touch any other parts of the :class:`Machine` instance
        it's a part of.
        """
        num_args = func.func_code.co_argcount
        def stack_helper(self):
            args = [self._pop() for x in xrange(num_args)]
            ret = func(*args)
            if ret is None:
                return
            try:
                self.data_stack.extend(ret)
            except TypeError:
                self.data_stack.append(ret)
        self.words[word] = types.MethodType(stack_helper, self)

    def eval(self, text=''):
        self.parser = Parser(text)

        ret = ''
        try:
            for word in self.parser.generate():
                token = self.tokenize_one(word)
                ret += self.interpret_one(*token)
        except ForthError as e:
            self.data_stack = []
            self.mode = IMMEDIATE_MODE
            return ret + ' ? ' + e.message

        if self.mode is IMMEDIATE_MODE:
            return ret + ' ok'
        elif self.mode is COMPILE_MODE:
            return ret + ' compiled'

    def tokenize(self, text):
        self.parser = Parser(text)
        ret = []
        for word in self.parser.generate():
            ret.append(self.tokenize_one(word))
        return ret

    def tokenize_one(self, word):
        try:
            number = int(word)
            return 'NUMBER', number
        except ValueError:
            pass  # ignore the failed conversion.

        if word in self.words:
            return 'CALL', self.words[word]
        else:
            return 'WORD', word

    def interpret(self, tokens=()):
        ret = ''
        for t in tokens:
            ret += self.interpret_one(*t)
        return ret

    def interpret_one(self, kind, token):
        if self.mode is IMMEDIATE_MODE:
            return self.interpret_one_immediate(kind, token)
        elif self.mode is COMPILE_MODE:
            return self.interpret_one_compile(kind, token)

    def interpret_one_immediate(self, kind, token):
        if kind == 'NUMBER':
            self.data_stack.append(token)
            return ''
        elif kind == 'CALL':
            output = token()
            if output is None:
                return ''
            return output
        elif kind == 'WORD':
            raise ForthError('undefined word: %s' % token)

    def interpret_one_compile(self, kind, token):
        if kind == 'CALL' and hasattr(token, 'is_compile_word') and token.is_compile_word:
            output = token()
            if output is None:
                return ''
            return output
        elif kind == 'WORD':
            raise ForthError('undefined word: %s' % token)
        else:
            self.compile_queue.append((kind, token))
            return ''
