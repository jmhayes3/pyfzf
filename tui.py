#!/usr/bin/env python3

import fcntl
import termios
import sys
import struct
import urwid
import signal
import re
import os
import subprocess

from matcher import compute_scores, fuzzymatch_v1

# TODO: add supoort for python 2.7
if (sys.version_info < (3, 0)):
    exit('Sorry, you need Python 3 to run this!')

palette = [
    ('head', '', '', '', '#000', '#618'),
    ('body', '', '', '', '#ddd', '#000'),
    ('focus', '', '', '', '#000', '#da0'),
    ('input', '', '', '', '#fff', '#618'),
    ('empty_list', '', '', '', '#ddd', '#b00'),
    ('pattern', '', '', '', '#f91', ''),
    ('pattern_focus', '', '', '', 'bold,#a00', '#da0'),
    ('line', '', '', '', '', ''),
    ('line_focus', '', '', '', '#000', '#da0'),
]

signal.signal(signal.SIGINT, lambda *_: sys.exit(0))  # die with style


class ItemWidget(urwid.WidgetWrap):
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ItemWidgetPlain(ItemWidget):
    def __init__(self, line):
        self.line = line
        text = urwid.AttrMap(urwid.Text(self.line), 'line', 'line_focus')
        super().__init__(text)


# TODO: highlight char where char index is equal to match index
class ItemWidgetPattern(ItemWidget):
    def __init__(self, line, match_indices=None):
        self.line = line

        # highlight chars where a match is found
        parts = []
        for char_index, char in enumerate(line):
            if char_index in match_indices:
                parts.append(('pattern', char))
            else:
                parts.append(char)

        text = urwid.AttrMap(
            urwid.Text(parts),
            'line',
            {'pattern': 'pattern_focus', None: 'line_focus'}
        )

        super().__init__(text)


class ItemWidgetWords(ItemWidget):
    def __init__(self, line, search_words):
        self.line = line

        subject = line
        parts = []
        for search_word in search_words:
            if search_word:
                split = subject.split(search_word, maxsplit=1)
                subject = split[-1]
                parts += [split[0], ('pattern', search_word)]

        try:
            parts += split[1]
        except IndexError:
            pass

        text = urwid.AttrMap(
            urwid.Text(parts),
            'line',
            {'pattern': 'pattern_focus', None: 'line_focus'}
        )

        super().__init__(text)


class SearchEdit(urwid.Edit):
    __metaclass__ = urwid.signals.MetaSignals
    signals = ['done', 'toggle_case_modifier']

    def keypress(self, size, key):
        if key == 'enter':
            urwid.emit_signal(self, 'done', self.get_edit_text())
            return
        elif key == 'esc':
            urwid.emit_signal(self, 'done', None)
            return
        elif key == 'tab':
            urwid.emit_signal(self, 'toggle_case_modifier')
            urwid.emit_signal(self, 'change', self, self.get_edit_text())
            return
        elif key == 'down':
            urwid.emit_signal(self, 'done', None)
            return

        urwid.Edit.keypress(self, size, key)


class ResultList(urwid.ListBox):
    __metaclass__ = urwid.signals.MetaSignals
    signals = ['resize']

    def __init__(self, *args):
        self.last_size = None
        urwid.ListBox.__init__(self, *args)

    def render(self, size, focus):
        if size != self.last_size:
            self.last_size = size
            urwid.emit_signal(self, 'resize', size)
        return urwid.ListBox.render(self, size, focus)


class LineCountWidget(urwid.Text):
    def update(self, relevant_lines=None, total_lines=None):
        if not hasattr(self, 'relevant_lines'):
            self.relevant_lines = 0
            self.total_lines = 0

        if relevant_lines is not None:
            self.relevant_lines = relevant_lines

        if total_lines is not None:
            self.total_lines = total_lines

        self.set_text('{}/{}'.format(self.relevant_lines, self.total_lines))


class Selector(object):
    def __init__(self, revert_order, case_sensitive, remove_duplicates, show_matches, infile):

        self.show_matches = show_matches
        self.case_modifier = case_sensitive

        self.lines = []

        self.line_widgets = []

        self.line_count_display = LineCountWidget('')
        self.search_edit = SearchEdit(edit_text='')

        self.modifier_display = urwid.Text('')

        urwid.connect_signal(self.search_edit, 'done', self.edit_done)
        urwid.connect_signal(self.search_edit, 'toggle_case_modifier', self.toggle_case_modifier)
        urwid.connect_signal(self.search_edit, 'change', self.edit_change)

        header = urwid.AttrMap(urwid.Columns([
            urwid.AttrMap(self.search_edit, 'input', 'input'),
            self.modifier_display,
            ('pack', self.line_count_display),
        ], dividechars=1, focus_column=0), 'head', 'head')

        self.item_list = urwid.SimpleListWalker(self.line_widgets)
        self.listbox = ResultList(self.item_list)

        urwid.connect_signal(self.listbox, 'resize', self.list_resize)

        self.view = urwid.Frame(body=self.listbox, header=header)

        self.loop = urwid.MainLoop(self.view, palette, event_loop=urwid.AsyncioEventLoop(), unhandled_input=self.on_unhandled_input)
        self.loop.screen.set_terminal_properties(colors=256)

        self.line_count_display.update(len(self.item_list), len(self.item_list))

        # TODO workaround, when update_list is called directly, the linecount widget gets not updated
        self.loop.set_alarm_in(0.01, lambda *loop: self.update_list(''))

        if infile.name == '<stdin>':
            # pipe = self.loop.watch_pipe(self.update_lines)
            pipe = subprocess.PIPE
            process = subprocess.Popen(
                ["find", ".",  "-not", "-path", "*/\.*", "-type", "f"],
                stdout=pipe,
                stderr=subprocess.DEVNULL
            )
            stdout, stderr = process.communicate()
            self.update_lines(stdout)

        self.loop.run()

    def list_resize(self, size):
        # self.line_count_display.update(relevant_lines=size[1])
        pass

    def toggle_case_modifier(self):
        self.case_modifier = not self.case_modifier
        self.update_modifiers()

    def update_modifiers(self):
        modifiers = []
        if self.case_modifier:
            modifiers.append('case')

        if len(modifiers) > 0:
            self.modifier_display.set_text('[{}]'.format(','.join(modifiers)))
        else:
            self.modifier_display.set_text('')

    def update_lines(self, data):
        lines = data.decode("UTF-8").split("\n")
        # last line is empty, remove it
        lines = lines[0:-1]
        for line in lines:
            # remove directory indicator prefix if it exists
            if line[0:2] == "./":
                line = line.replace("./", "", 1)

            if line not in self.lines:
                self.lines.append(line)

        self.item_list[:] = [ItemWidgetPlain(item) for item in self.lines]
        self.line_count_display.update(total_lines=len(self.item_list))

    def update_list(self, search_text):
        if search_text == '' or search_text == '"' or search_text == '""':  # show all lines
            self.item_list[:] = [ItemWidgetPlain(item) for item in self.lines]
            self.line_count_display.update(len(self.item_list))
        else:
            # get scores
            # sort by score
            # sort lines in ascending order by score and line length
            # sorted_by_score = sorted(processed, key=lambda x: (x[1], len(x[0])), reverse=False)

            scored_lines = []
            for index, line in enumerate(self.lines):
                score, match_positions = fuzzymatch_v1(line, search_text)
                scored_lines.append((index, line, score, match_positions))

            lines_sorted_by_score = sorted(scored_lines, key=lambda x: (x[2], len(x[1])), reverse=True)

            items = []
            for item in lines_sorted_by_score:
                if item[2] > 0:
                    if self.show_matches:
                        items.append(ItemWidgetPattern(item[1], match_indices=item[3]))
                    else:
                        items.append(ItemWidgetPlain(item[1]))

            if len(items) > 0:
                self.item_list[:] = items
                self.line_count_display.update(relevant_lines=len(self.item_list))
            else:
                self.item_list[:] = [urwid.Text(('empty_list', 'No selection'))]
                self.line_count_display.update(relevant_lines=0)

        try:
            self.item_list.set_focus(0)
        except IndexError:  # no items
            pass

    def edit_change(self, widget, search_text):
        self.update_list(search_text)

    def edit_done(self, search_text):
        self.view.set_focus('body')

    def on_unhandled_input(self, input_):
        if isinstance(input_, tuple):  # mouse events
            return True

        if input_ == 'enter':
            try:
                line = self.listbox.get_focus()[0].line
            except AttributeError:  # empty list
                return

            self.view.set_header(urwid.AttrMap(
                urwid.Text('selected: {}'.format(line)), 'head'))

            self.inject_command(line)
            raise urwid.ExitMainLoop()

        elif input_ == 'tab':
            self.toggle_case_modifier()

        elif input_ == 'backspace':
            self.search_edit.set_edit_text(self.search_edit.get_text()[0][:-1])
            self.search_edit.set_edit_pos(len(self.search_edit.get_text()[0]))
            self.view.set_focus('header')

        elif input_ == 'esc':
            raise urwid.ExitMainLoop()

        elif len(input_) == 1:  # ignore things like tab, enter
            self.search_edit.set_edit_text(self.search_edit.get_text()[0] + input_)
            self.search_edit.set_edit_pos(len(self.search_edit.get_text()[0]))
            self.view.set_focus('header')

        return True

    def inject_command(self, command):
        command = (struct.pack('B', c) for c in os.fsencode(command))

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ECHO  # disable echo
        termios.tcsetattr(fd, termios.TCSANOW, new)
        for c in command:
            fcntl.ioctl(fd, termios.TIOCSTI, c)
        termios.tcsetattr(fd, termios.TCSANOW, old)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--revert-order', action='store_true', default=False, help='revert the order of the lines')
    parser.add_argument('-a', '--case-sensitive', action='store_true', default=True, help='start in case-sensitive mode')
    parser.add_argument('-d', '--remove-duplicates', action='store_true', default=True, help='remove duplicated lines')
    parser.add_argument('-y', '--show-matches', action='store_true', default=True, help='highlight the part of each line where there is a match')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin, help='the file which lines you want to select eg. <(history)')

    args = parser.parse_args()

    Selector(
        revert_order=args.revert_order,
        case_sensitive=args.case_sensitive,
        remove_duplicates=args.remove_duplicates,
        show_matches=args.show_matches,
        infile=args.infile,
        # TODO support missing options
    )


if __name__ == '__main__':
    main()

