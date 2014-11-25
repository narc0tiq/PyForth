# coding= utf-8
from __future__ import unicode_literals

from forth.parser import Parser

import inspect
import types

class ForthError(Exception): pass


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
            func.word = func.func_name
        else:
            func.word = name
        return func
    return decorator

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

        for name, method in inspect.getmembers(self, predicate=lambda meth: hasattr(meth, 'word')):
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

    def _add_stackmethod(self, word, func):
        self.words[word] = types.MethodType(_stackmethod(func), self)

    def tokenize(self, text):
        if self.parser is None or self.parser.is_finished:
            self.parser = Parser(text)

        ret = []
        for word in self.parser.generate():
            try:
                number = int(word)
                ret.append(('NUMBER', number))
                continue
            except ValueError:
                pass  # ignore the failed conversion.

            ret.append(('WORD', word))

        return ret

    def interpret(self, tokens=()):
        ret = ''

        try:
            for t, v in tokens:
                if t == 'NUMBER':
                    self.data_stack.append(v)
                elif t == 'WORD':
                    if v not in self.words:
                        raise(ForthError('undefined word: %s' % v))

                    output = self.words[v]()
                    if output is not None:
                        ret += output
        except ForthError as e:
            self.data_stack = []
            return ret + ' ? ' + e.message

        return ret + ' ok'

    def eval(self, text=''):
        return self.interpret(self.tokenize(text))
