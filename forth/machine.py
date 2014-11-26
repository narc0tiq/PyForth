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

def _stackmethod(meth):
    """
    Turns a Python method (NOT a function!) into a stack-consumer. The
    method's arguments are passed in from the stack in the order they pop
    off the stack, thus from the stack [1, 2, 3], (lambda self,a,b: a+b) will
    receive a=3, b=2.

    The return value, if any, is assumed to go on the stack, and an empty
    string is assumed for output. If you need output, don't use this!
    """
    def decorated(self):
        num_args = meth.func_code.co_argcount - 1  # ignore leading self arg
        args = [self._pop() for x in xrange(num_args)]
        ret = meth(self, *args)
        if ret is None:
            return
        try:
            self.data_stack.extend(ret)
        except TypeError:
            self.data_stack.append(ret)
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

        self._add_stackmethod('+', lambda self, b, a: a + b)
        self._add_stackmethod('-', lambda self, b, a: a - b)
        self._add_stackmethod('*', lambda self, b, a: a * b)
        self._add_stackmethod('/', lambda self, b, a: a / b)
        self._add_stackmethod('MOD', lambda self, b, a: a % b)
        self._add_stackmethod('/MOD', lambda self, b, a: reversed(divmod(a, b)))
        self._add_stackmethod('SWAP', lambda self, b, a: (b, a))
        self._add_stackmethod('DUP', lambda self, a: (a, a))
        self._add_stackmethod('OVER', lambda self, b, a: (a, b, a))
        self._add_stackmethod('ROT', lambda self, c, b, a: (b, c, a))
        self._add_stackmethod('DROP', lambda self, a: None)
        self._add_stackmethod('TUCK', lambda self, b, a: (b, a, b))

        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, 'word'):
                self.words[method.word] = method

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

    def _add_stackmethod(self, word, func):
        self.words[word] = types.MethodType(_stackmethod(func), self)

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
