from __future__ import unicode_literals, print_function
import forth
import readline

PROMPT = ''

def forth_repl():
    print('Type "BYE" or input an end of file (Ctrl+D) to quit.')

    m = forth.Machine()

    cmd = raw_input(PROMPT)
    while cmd.upper() != 'BYE':
        print(m.eval(cmd))
        cmd = raw_input(PROMPT)


if __name__ == '__main__':
    try:
        forth_repl()
    except EOFError:
        pass  # perfectly acceptable
