# coding= utf-8
"""
Tests the forth.Machine as an open box, i.e., with some knowledge of its
internals and the ability to dig into them.

See :file:`test_black_box.py` for the more opaque tests.
"""
from __future__ import unicode_literals

import forth


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

# TODO: eval(': STAR 42 EMIT ;') and verify the word STAR gets created and
# returns '*' when called.
