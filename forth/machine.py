# coding= utf-8
from __future__ import unicode_literals

from forth.parser import Parser

import inspect
import types

class ForthError(Exception): pass
class ImmediateQuit(ForthError): pass
class LeaveLoop(ForthError): pass

IMMEDIATE_MODE = 9900
COMPILE_MODE = 9901


def _word(*names):
    """
    Creates a decorator that adds a .words member to its given func, which may
    then be inspected for by the :class:`Machine`'s __init__ method. Note that
    if you already have an instance of :class:`Machine`, it's too late to
    decorate and you should call its :method:`Machine._add_stackmethod`
    instead.
    """
    def decorator(func):
        func.words = names
        return func
    return decorator

def _compile_word(meth):
    """
    Provides some automatic behaviour for :func:`@_word`s which are
    compile-only words: raising an error if the :class:`Machine` is not in
    compile mode.
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
        self.return_stack = []

        # Add decorated member words
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, 'words'):
                for word in method.words:
                    self.words[word] = method

        # Add basic math and stack handling
        self.add_stackmethod('+', lambda b, a: a + b)
        self.add_stackmethod('-', lambda b, a: a - b)
        self.add_stackmethod('*', lambda b, a: a * b)
        self.add_stackmethod('/', lambda b, a: a / b)
        self.add_stackmethod('MOD', lambda b, a: a % b)
        self.add_stackmethod('/MOD', lambda b, a: reversed(divmod(a, b)))

        self.add_stackmethod('>', lambda b, a: -1 if a > b else 0)
        self.add_stackmethod('>=', lambda b, a: -1 if a >= b else 0)
        self.add_stackmethod('<', lambda b, a: -1 if a < b else 0)
        self.add_stackmethod('<=', lambda b, a: -1 if a <= b else 0)
        self.add_stackmethod('==', lambda b, a: -1 if a == b else 0)
        self.add_stackmethod('!=', lambda b, a: -1 if a != b else 0)

        self.add_stackmethod('INVERT', lambda a: ~a)

        self.add_stackmethod('SWAP', lambda b, a: (b, a))
        self.add_stackmethod('DUP', lambda a: (a, a))
        self.add_stackmethod('OVER', lambda b, a: (a, b, a))

        self.add_stackmethod('2DUP', lambda b, a: (a, b, a, b))
        self.add_stackmethod('2SWAP', lambda d, c, b, a: (c, d, a, b))
        self.add_stackmethod('2OVER', lambda d, c, b, a: (a, b, c, d, a, b))

        self.add_stackmethod('ROT', lambda c, b, a: (b, c, a))
        self.add_stackmethod('DROP', lambda a: None)
        self.add_stackmethod('TUCK', lambda b, a: (b, a, b))

    def _push(self, val):
        self.data_stack.append(val)

    def _push_all(self, ls):
        self.data_stack.extend(ls)

    def _pop(self):
        if self.data_stack:
            return self.data_stack.pop()
        else:
            raise ForthError('stack underflow')

    def _pop_until(self, predicate):
        ret = []
        while True:
            val = self._pop()
            ret.append(val)
            if predicate(val):
                return ret

    def _return_push(self, val):
        self.return_stack.append(val)

    def _return_pop(self):
        if self.return_stack:
            return self.return_stack.pop()
        else:
            raise ForthError('return stack underflow')

    @_word('.')
    def _print_pop(self):
        return str(self._pop()) + ' '

    @_word('.S')
    def _print_stack(self):
        return repr(self.data_stack) + ' '

    @_word('WORDS')
    def _print_words(self):
        return ' '.join(sorted(self.words.keys()))

    @_word('EMIT')
    def _emit(self):
        value = self._pop()
        return unichr(value)

    @_word(':')
    def _begin_compile(self):
        try:
            new_word = self.parser.next_word()
        except StopIteration:
            raise ForthError('no name given')

        self.mode = COMPILE_MODE
        self.now_compiling = new_word
        self._return_push(':')
        self._push(':')

    @_word(';')
    @_compile_word
    def _end_compile(self):
        opened = self._return_pop()
        if opened != ':':
            raise ForthError('unclosed %s' % opened)

        tokens = self._pop_until(lambda tok: tok == ':')[-2::-1]
        new_word = lambda self: self.interpret(tokens)
        self.words[self.now_compiling] = types.MethodType(new_word, self)

        self.mode = IMMEDIATE_MODE
        self.now_compiling = None

    @_word('DO')
    @_compile_word
    def _begin_do_loop(self):
        self._return_push('DO')
        self._push('DO')

    def _acquire_do_loop_contents(self):
        opened = self._return_pop()
        if opened == ':':
            raise ForthError('missing DO')
        if opened != 'DO':
            raise ForthError('unclosed %s' % opened)

        return self._pop_until(lambda tok: tok == 'DO')[-2::-1]

    @_word('LOOP')
    @_compile_word
    def _end_do_loop(self):
        loop_tokens = self._acquire_do_loop_contents()
        # HAX? Loops end with a number defining the step size --
        # DO..LOOP implies a step size of 1.
        loop_tokens.append(('NUMBER', 1))
        self._push(('LOOP', loop_tokens))

    @_word('+LOOP')
    @_compile_word
    def _end_plus_loop(self):
        loop_tokens = self._acquire_do_loop_contents()
        self._push(('LOOP', loop_tokens))

    @_word('BEGIN')
    @_compile_word
    def _begin_while_loop(self):
        self._return_push('BEGIN')
        self._push('BEGIN')

    @_word('UNTIL')
    @_compile_word
    def _end_until_loop(self):
        opened = self._return_pop()
        if opened == ':':
            raise ForthError('missing BEGIN')
        if opened != 'BEGIN':
            raise ForthError('unclosed %s' % opened)

        # Use the Forth machine itself to invert the UNTIL into a WHILE:
        self.interpret(self.tokenize('IF 0 ELSE -1 THEN'))

        begin_tokens = self._pop_until(lambda tok: tok == 'BEGIN')[-2::-1]

        self._push(('WHILE', (begin_tokens,())))

    @_word('WHILE')
    @_compile_word
    def _mid_while_loop(self):
        opened = self._return_pop()
        if opened == ':':
            raise ForthError('missing BEGIN')
        if opened != 'BEGIN':
            raise ForthError('unclosed %s' % opened)
        self._return_push(opened)
        self._return_push('WHILE')
        self._push('WHILE')

    @_word('REPEAT')
    @_compile_word
    def _end_while_loop(self):
        opened = self._return_pop()
        if opened == ':':
            raise ForthError('missing WHILE')
        if opened != 'WHILE':
            raise ForthError('unclosed %s' % opened)

        assert self._return_pop() == 'BEGIN'

        while_tokens = self._pop_until(lambda tok: tok == 'WHILE')[-2::-1]
        begin_tokens = self._pop_until(lambda tok: tok == 'BEGIN')[-2::-1]

        self._push(('WHILE', (begin_tokens, while_tokens)))

    @_word('IF')
    @_compile_word
    def _if(self):
        self._return_push('IF')
        self._push('IF')

    @_word('ELSE')
    @_compile_word
    def _else(self):
        opened = self._return_pop()
        if opened != 'IF':
            raise ForthError('missing IF')
        self._return_push(opened)
        self._return_push('ELSE')
        self._push('ELSE')

    @_word('THEN')
    @_compile_word
    def _then(self):
        opened = self._return_pop()
        if opened != 'IF' and opened != 'ELSE':
            raise ForthError('missing IF')

        false_tokens = ()
        if opened == 'ELSE':
            false_tokens = self._pop_until(lambda tok: tok == 'ELSE')[-2::-1]
            opened = self._return_pop()

        assert opened == 'IF' # I can't imagine how it would fail to be.
        true_tokens = self._pop_until(lambda tok: tok == 'IF')[-2::-1]

        self._push(('BRANCH', (true_tokens, false_tokens)))

    @_word('COMPILE_WORD_WITH_OUTPUT_FOR_TESTING')
    @_compile_word
    def test_compiler_output(self):
        return 'SOME OUTPUT!!!'

    @_word('QUIT')
    def interpreter_quit(self):
        raise ImmediateQuit()

    @_word('LEAVE')
    @_compile_word
    def compile_leave_loop(self):
        self._push(('LEAVE', None))

    @_word('>R')
    def move_data_to_return(self):
        self._return_push(self._pop())

    @_word('R>')
    def move_return_to_data(self):
        self._push(self._return_pop())

    @_word('R@', 'I')
    def copy_return_to_data(self):
        tors = self._return_pop()
        self._return_push(tors)
        self._push(tors)

    @_word('J')
    def copy_outer_loop_to_data(self):
        i = self._return_pop()
        j = self._return_pop()

        self._return_push(j)
        self._return_push(i)

        self._push(j)

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
                self._push_all(ret)
            except TypeError:
                self._push(ret)
        self.words[word] = types.MethodType(stack_helper, self)

    def eval(self, text=''):
        self.parser = Parser(text)

        ret = ''
        try:
            for word in self.parser.generate():
                token = self.tokenize_one(word)
                ret += self.interpret_one(*token)
        except ImmediateQuit:
            return ret
        except ForthError as e:
            self.data_stack = []
            self.return_stack = []
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

    def interpret_loop(self, tokens):
        index = self._pop()
        loop_end = self._pop()

        ret = ''
        while index < loop_end:
            self._return_push(index)
            try:
                ret += self.interpret(tokens)
            except LeaveLoop:
                break
            index = self._return_pop()
            index += self._pop()

        return ret

    def interpret_branch(self, true_tokens, false_tokens):
        testvar = self._pop()

        ret = ''
        if testvar:
            ret += self.interpret(true_tokens)
        else:
            ret += self.interpret(false_tokens)

        return ret

    def interpret_while(self, begin_tokens, while_tokens):
        ret = ''
        while True:
            ret += self.interpret(begin_tokens)
            testvar = self._pop()
            if not testvar:
                break
            ret += self.interpret(while_tokens)

        return ret

    def interpret_one_immediate(self, kind, token):
        if kind == 'NUMBER':
            self._push(token)
            return ''
        elif kind == 'CALL':
            output = token()
            if output is None:
                return ''
            return output
        elif kind == 'LOOP':
            return self.interpret_loop(token)
        elif kind == 'BRANCH':
            return self.interpret_branch(*token)
        elif kind == 'WHILE':
            return self.interpret_while(*token)
        elif kind == 'WORD':
            raise ForthError('undefined word: %s' % token)
        elif kind == 'LEAVE':
            raise LeaveLoop('not looping')
        else:
            raise ForthError('unknown token type: %s' % kind)

    def interpret_one_compile(self, kind, token):
        if kind == 'CALL' and hasattr(token, 'is_compile_word') and token.is_compile_word:
            output = token()
            if output is None:
                return ''
            return output
        elif kind == 'WORD':
            raise ForthError('undefined word: %s' % token)
        else:
            self._push((kind, token))
            return ''
