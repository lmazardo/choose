import re
import shutil
import sys
import tty
import termios
import os

ESC = '\x1b'
RESET = ESC + '[0m'
COLOR = ESC + '[31m'
HOME = ESC + '[H'
ALTERNATE_BUFFER_ON = ESC + '7' + ESC + '[?47h'
ALTERNATE_BUFFER_OFF = ESC + '[?47l' + ESC + '8'
SHOW_CURSOR = ESC + '[?25h'
HIDE_CURSOR = ESC + '[?25l'

ESCKEYS = {
    '[A': 'up',
    '[B': 'down',
}

MAPPINGS = {
    '\x0e': 'down',  # ctrl+n
    '\x10': 'up',    #ctrl+p
    '\x04': 'screen down', # ctrl+d
}


firstline = 'Navigate with ↑ and ↓, `return` exits and prints currently selected line'


class Console():
    def __enter__(self):
        self.old_out = sys.stdout
        self.old_in = sys.stdin
        sys.__stdout__ = sys.stdout = open('/dev/tty', 'w')
        sys.__stdin__ = sys.stdin = open('/dev/tty', 'r')
        self.fd_stdin = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd_stdin)
        tty.setcbreak(self.fd_stdin)

        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.write(ALTERNATE_BUFFER_ON)

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write(ALTERNATE_BUFFER_OFF)
        sys.stdout.flush()
        termios.tcsetattr(self.fd_stdin, termios.TCSADRAIN, self.old_settings)
        sys.__stdout__ = sys.stdout = self.old_out
        sys.__stdin__ = sys.stdin = self.old_in


def get_input():
    ch = sys.stdin.read(1)
    ch = MAPPINGS.get(ch, ch)
    if ch == ESC:
        ch = ESCKEYS.get(sys.stdin.read(2))
    return ch


def out(line, width, color=''):
    line = line[:width].ljust(width)
    if color:
        line = color + line + RESET
    sys.stdout.write(line)


def render(data, width, height, focus, lastline):
    framecolor = ESC + '[44m' + ESC + '[37m'
    highlight = ESC + '[47m' + ESC + '[34m'

    sys.stdout.write(ESC + '[1;1H')
    out(firstline, width, color=framecolor)

    if focus + height - 2 > len(data):
        lower = max(0, len(data) - height + 2)
    else:
        lower = focus

    termno = 2
    for lineno in range(lower, lower + height - 2):
        sys.stdout.write(ESC + '[{};1H'.format(termno))
        try:
            color = highlight if lineno == focus else ''
            out(data[lineno], width, color)
        except IndexError:
            out('', width)
        termno += 1
    sys.stdout.write(ESC + '[{};1H'.format(termno))
    out(lastline, width, color=framecolor)
    sys.stdout.flush()


def adjust_focus(data, focus, key):
    if key == 'down' and focus < len(data) - 1:
        return focus + 1
    elif key == 'up' and not focus == 0:
        return focus - 1
    else:
        return focus


def filter_fuzzy(data, string):
    regex = re.compile('.*'.join(string), re.I)
    return [line for line in data if regex.search(line)]


def filter_regex(data, string):
    regex = re.compile(string)
    return [line for line in data if regex.search(line)]

if __name__ == '__main__':
    data = [line.strip('\n') for line in sys.stdin.readlines()]
    with Console():
        focus = 0
        filter_mode = 0
        filters = [
            (filter_fuzzy, 'fuzzy'),
            (filter_regex, 'regex'),
        ]

        search_term, last_search_term = '', ''
        mydata = data
        rprint = False
        while True:
            width, height = shutil.get_terminal_size()
            filter_fun = filters[filter_mode][0]
            if last_search_term != search_term:
                mydata = filter_fun(data, search_term)
                last_search_term = search_term
                if focus > len(mydata):
                    focus = len(mydata) - 1
            if search_term:
                lastline = '({}) Searching for: {}'.format(filters[filter_mode][1], search_term)
            else:
                lastline = 'Start typeing for search, ctrl-t for switching search mode'
            render(mydata, width, height, focus, lastline=lastline)
            key = get_input()
            if key in ['up', 'down']:
                focus = adjust_focus(mydata, focus, key)
            elif key in ['\r', '\n']:
                rprint = mydata[focus]
                break
            elif key in ['\x7f']:  # backspace
                search_term = search_term[:-1]
            elif key in ['\x03']:  # ctrl-c
                break
            elif key in ['\x14']:  # ctrl-t, bad-choice
                filter_mode = (filter_mode + 1) % len(filters)
            elif key is not None:
                search_term = search_term + key
    if rprint:
        print(rprint)
    sys.exit(0)
