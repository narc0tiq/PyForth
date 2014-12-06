# coding= utf-8
"""
Tests the forth.Machine as an open box, i.e., with some knowledge of its
internals and the ability to dig into them.

See :file:`test_black_box.py` for the more opaque tests.
"""
from __future__ import unicode_literals

import forth
import pytest


class TestOpenBoxForth():
    def test_blank_line(self):
        m = forth.Machine()
        ret = m.eval("\n")

        assert ret == ' ok'

    def test_number_to_stack(self):
        m = forth.Machine()
        ret = m.eval("42")

        assert ret == ' ok'
        assert 42 in m.data_stack

    def test_negative_numer(self):
        m = forth.Machine()
        ret = m.eval('-12')

        assert ret == ' ok'
        assert -12 in m.data_stack

    def test_two_numbers(self):
        m = forth.Machine()
        ret = m.eval('1 2')

        assert ret == ' ok'
        assert m.data_stack == [1, 2]

    def test_stack_pop(self):
        m = forth.Machine()
        ret = m.eval('42 .')

        assert ret == '42  ok'
        assert not m.data_stack

    def test_stack_underflow(self):
        m = forth.Machine()
        ret = m.eval('.')

        assert ret == ' ? stack underflow'  # "Note that a stack underflow is NOT ok."
        assert not m.data_stack

    def test_stack_pop_two(self):
        m = forth.Machine()
        ret = m.eval('1 2 . .')

        assert ret == '2 1  ok'
        assert not m.data_stack

    def test_stack_one_pop_two(self):
        m = forth.Machine()
        ret = m.eval('1 . .')
        assert ret == '1  ? stack underflow'
        assert not m.data_stack

    def test_stack_underflow_cancels(self):
        m = forth.Machine()
        ret = m.eval('. 43')

        assert ret == ' ? stack underflow'
        assert not m.data_stack

    def test_simple_math(self):
        for oper, expected in { '+': 24, '-': 16, '*': 80, '/': 5, 'MOD': 0 }.iteritems():
            m = forth.Machine()
            ret = m.eval('20 4 ' + oper)

            assert ret == ' ok'
            assert expected in m.data_stack

    def test_divmod(self):
        m = forth.Machine()
        ret = m.eval('17 3 /MOD')

        assert ret == ' ok'
        assert m.data_stack == [2, 5]

    def test_swap(self):
        m = forth.Machine()
        ret = m.eval('5 12 SWAP')

        assert ret == ' ok'
        assert m.data_stack == [12, 5]

    def test_two_operand_underflow(self):
        for oper in ['+', '-', '*', '/', 'MOD', '/MOD', 'SWAP']:
            m = forth.Machine()
            ret = m.eval('1 ' + oper)

            assert ret == ' ? stack underflow'
            assert not m.data_stack

    def test_dup(self):
        m = forth.Machine()
        ret = m.eval('9 DUP')

        assert ret == ' ok'
        assert m.data_stack == [9, 9]

        m = forth.Machine()
        ret = m.eval('DUP')

        assert ret == ' ? stack underflow'

    def test_over(self):
        m = forth.Machine()
        ret = m.eval('1 2 OVER')

        assert ret == ' ok'
        assert m.data_stack == [1, 2, 1]

        m = forth.Machine()
        ret = m.eval('1 OVER')

        assert ret == ' ? stack underflow'

    def test_rot(self):
        m = forth.Machine()
        ret = m.eval('1 2 3 ROT')

        assert ret == ' ok'
        assert m.data_stack == [2, 3, 1]

        m = forth.Machine()
        ret = m.eval('1 2 ROT')

        assert ret == ' ? stack underflow'

    def test_drop(self):
        m = forth.Machine()
        ret = m.eval('1 DROP')

        assert ret == ' ok'
        assert not m.data_stack

        m = forth.Machine()
        ret = m.eval('DROP')

        assert ret == ' ? stack underflow'

    def test_tuck(self):
        m = forth.Machine()
        ret = m.eval('1 2 TUCK')

        assert ret == ' ok'
        assert m.data_stack == [2, 1, 2]

        m = forth.Machine()
        ret = m.eval('1 TUCK')

        assert ret == ' ? stack underflow'

    def test_unknown_word(self):
        m = forth.Machine()
        ret = m.eval('UNKNOWN_WORD')

        assert ret == ' ? undefined word: UNKNOWN_WORD'

    def test_tokenize(self):
        m = forth.Machine()
        interpreted = m.tokenize('23 *')

        assert interpreted == [('NUMBER', 23), ('CALL', m.words['*'])]

    def test_multi_eval(self):
        m = forth.Machine()
        ret = m.eval('12 34')

        assert ret == ' ok'
        assert m.data_stack == [12, 34]

        ret = m.eval('+')
        assert ret == ' ok'
        assert m.data_stack == [46]

    def test_multiline_eval(self):
        m = forth.Machine()
        ret = m.eval('1 2\n+')

        assert ret == ' ok'
        assert m.data_stack == [3]

    def test_interpret(self):
        m = forth.Machine()
        ret = m.interpret([('NUMBER', 42),
                           ('NUMBER', 30),
                           ('CALL', m.words['.'])])

        assert ret == '30 '
        assert m.data_stack == [42]

    def test_error_clears_stack(self):
        m = forth.Machine()
        ret = m.eval('42')

        assert ret == ' ok'
        assert m.data_stack == [42]

        ret = m.eval('NO-SUCH-WORD')

        assert 'undefined word' in ret
        assert not m.data_stack

    def test_emit(self):
        m = forth.Machine()
        ret = m.eval('42 EMIT')

        assert ret == '* ok'

    def test_printstack(self):
        m = forth.Machine()
        ret = m.eval('42 1 2 3 .S')

        assert m.data_stack == [42, 1, 2, 3]
        # Kind of a fragile test, as it relies on the implementation of .S
        # always including repr(self.data_stack), which it might not do in
        # future. Nonetheless, it's currently sufficiently correct.
        assert repr(m.data_stack) in ret

    def test_compile_only_word(self):
        m = forth.Machine()
        ret = m.eval(';')

        assert ret == ' ? compile-only word'

    def test_nameless_compile(self):
        m = forth.Machine()
        ret = m.eval(':')

        assert ret == ' ? no name given'

    def test_begin_compile(self):
        m = forth.Machine()
        ret = m.eval(': STAR')

        assert ret == ' compiled'
        assert m.mode is forth.COMPILE_MODE

    def test_bad_compile(self):
        m = forth.Machine()
        ret = m.eval(': STAR NO-SUCH-WORD')

        assert 'undefined word' in ret
        assert 'NO-SUCH-WORD' in ret
        assert m.mode is forth.IMMEDIATE_MODE

    def test_complete_compile(self):
        m = forth.Machine()
        ret = m.eval(': STAR 42 EMIT ;')

        assert 'ok' in ret
        assert 'STAR' in m.words
        assert m.data_stack == []
        assert m.mode is forth.IMMEDIATE_MODE

        ret = m.eval('STAR')

        assert ret == '* ok'
        assert m.data_stack == []

    def test_two_part_compile(self):
        m = forth.Machine()
        ret = m.eval(': STAR')
        ret = m.eval('42 EMIT')

        assert ret == ' compiled'
        assert ':' in m.data_stack
        assert m.compile_stack == [':']
        assert m.mode is forth.COMPILE_MODE
        assert 'STAR' not in m.words

        ret = m.eval(';')
        assert ret == ' ok'
        assert m.data_stack == []
        assert not m.compile_stack
        assert m.mode is forth.IMMEDIATE_MODE
        assert 'STAR' in m.words

        ret = m.eval('STAR STAR')

        assert ret == '** ok'
        assert m.data_stack == []

    def test_compile_word_with_output(self):
        m = forth.Machine()
        ret = m.eval(': STAR COMPILE_WORD_WITH_OUTPUT_FOR_TESTING')

        assert 'SOME OUTPUT' in ret
        assert m.mode is forth.COMPILE_MODE

    def test_compile_only_do(self):
        m = forth.Machine()
        ret = m.eval('5 0 DO 42 EMIT LOOP')

        assert 'compile-only' in ret
        assert '*' not in ret

    def test_unclosed_do(self):
        m = forth.Machine()
        ret = m.eval(': STARS 0 DO 42 EMIT ;')

        assert 'unclosed DO' in ret
        assert '*' not in ret

    def test_unopened_do(self):
        m = forth.Machine()
        ret = m.eval(': STARS 42 EMIT LOOP ;')

        assert 'missing DO' in ret
        assert '*' not in ret

    def test_underflow_do(self):
        m = forth.Machine()
        ret = m.eval(': STARS 0 DO 42 EMIT LOOP ; STARS')

        assert 'underflow' in ret
        assert '*' not in ret

    def test_loop(self):
        m = forth.Machine()
        ret = m.eval(': STARS 0 DO 42 EMIT LOOP ; 5 STARS')

        assert '*****' in ret
        assert 'ok' in ret

    def test_plus_loop(self):
        m = forth.Machine()

        assert 'missing DO' in m.eval(': OOPS +LOOP ;')
        assert 'underflow' in m.eval(': OOPS 2 0 DO 42 EMIT +LOOP ; OOPS')
        ret = m.eval(': JUMP-TWO DO 42 EMIT 2 +LOOP ; 4 0 JUMP-TWO')

        assert ret == '** ok'

    def test_unknown_token_type(self):
        m = forth.Machine()
        with pytest.raises(forth.ForthError) as excinfo:
            m.interpret_one_immediate('BAD-TOKEN', 'oops')

        assert 'unknown token' in str(excinfo.value)

    def test_wrong_loop_close(self):
        m = forth.Machine()
        ret = m.eval(': BLAH')

        m.compile_stack.append('OOPSIE')
        ret = m.eval('LOOP')

        assert 'unclosed OOPSIE' in ret

    def test_multi_loop(self):
        m = forth.Machine()
        ret = m.eval(': CR 10 EMIT ;\n'
                     ': STAR 42 EMIT ;\n'
                     ': STARS 0 DO STAR LOOP ;\n'
                     ': STAR-LINES 0 DO 5 STARS CR LOOP ;\n'
                     '2 STAR-LINES')

        assert ret == '*****\n*****\n ok'

        m = forth.Machine()
        ret = m.eval(': CR 10 EMIT ;\n'
                     ': STAR-LINES 0 DO 5 0 DO 42 EMIT LOOP CR LOOP ;\n'
                     '2 STAR-LINES')

        assert ret == '*****\n*****\n ok'

    def test_words(self):
        m = forth.Machine()
        ret = m.eval('WORDS')

        for word in m.words.keys():
            assert word in ret

    def test_compile_only_if_parts(self):
        m = forth.Machine()

        assert 'compile-only' in m.eval('IF')
        assert 'compile-only' in m.eval('ELSE')
        assert 'compile-only' in m.eval('THEN')

    def test_unclosed_if_else(self):
        m = forth.Machine()
        assert 'unclosed IF' in m.eval(': TEST IF ;')
        assert 'unclosed ELSE' in m.eval(': TEST IF ELSE ;')

    def test_unopened_if(self):
        m = forth.Machine()

        assert 'missing IF' in m.eval(': TEST ELSE')
        assert 'missing IF' in m.eval(': TEST THEN')

    def test_if_else_on_stack(self):
        m = forth.Machine()
        ret = m.eval(': TEST IF ELSE')

        assert 'compiled' in ret
        assert 'IF' in m.compile_stack
        assert 'ELSE' in m.compile_stack
        assert 'IF' in m.data_stack
        assert 'ELSE' in m.data_stack

    def test_if(self):
        m = forth.Machine()
        ret = m.eval(': TEST IF 42 ELSE 33 THEN . ;')

        assert ret == ' ok'
        assert 'TEST' in m.words
        assert not m.data_stack
        assert not m.compile_stack

        assert m.eval('1 TEST 0 TEST') == '42 33  ok'
        assert 'stack underflow' in m.eval('TEST')

    def test_empty_if(self):
        m = forth.Machine()
        ret = m.eval(': TEST IF ELSE THEN ; 1 TEST')

        assert ret == ' ok'
        assert 'TEST' in m.words
        assert not m.data_stack
        assert not m.compile_stack

        ret = m.eval(': TEST IF 42 EMIT THEN ; 1 TEST 0 TEST')
        assert ret == '* ok'

