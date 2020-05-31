import fcntl
import termios
import sys
import struct
import urwid
import signal
import re
import os
import subprocess

from matcher import fuzzymatch_v1


if (sys.version_info < (3, 4)):
    exit('pyfzf requires Python 3.4 or higher.')

palette = [
    ('head', '', '', '', '#000', '#618'),
    ('body', '', '', '', '#ddd', '#000'),
    ('foot', '', '', '', '#000', '#618'),
    ('focus', '', '', '', '#000', '#da0'),
    ('input', '', '', '', '#fff', '#618'),
    ('prompt', '', '', '', '#000', '#618'),
    ('prompt_focus', '', '', '', '#000', '#618'),
    ('empty_list', '', '', '', '#ddd', '#b00'),
    ('pattern', '', '', '', '#f91', ''),
    ('pattern_focus', '', '', '', 'bold,#a00', '#da0'),
    ('line', '', '', '', '', ''),
    ('line_focus', '', '', '', '#000', '#da0'),
]

signal.signal(signal.SIGINT, lambda *_: sys.exit(0))  # die with style


class LineItemWidget(urwid.WidgetWrap):
    def __init__(self, line, match_indices=None):
        self.line = line

        # highlight chars where a match is found
        if match_indices:
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
        else:
            text = urwid.AttrMap(urwid.Text(self.line), 'line', 'line_focus')

        super().__init__(text)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


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
        elif key == 'up':
            urwid.emit_signal(self, 'done', None)
            return
        elif key == 'down':
            urwid.emit_signal(self, 'done', None)
            return

        urwid.Edit.keypress(self, size, key)


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
    def __init__(self, algo, case_sensitive, show_matches, infile):
        self.algo = algo
        self.show_matches = show_matches
        self.case_modifier = case_sensitive
        self.infile = infile

        self.lines = []

        self.line_widgets = []

        self.line_count_display = LineCountWidget('')
        self.modifier_display = urwid.Text('')
        self.search_edit = SearchEdit(edit_text='')

        urwid.connect_signal(self.search_edit, 'done', self.edit_done)
        urwid.connect_signal(self.search_edit, 'toggle_case_modifier', self.toggle_case_modifier)
        urwid.connect_signal(self.search_edit, 'change', self.edit_change)

        self.status_line = urwid.AttrMap(
            urwid.Columns(
                [('pack', self.line_count_display),
                    self.modifier_display,
                ], dividechars=1),
            'line',
            'line_focus'
        )

        footer = urwid.Pile([
            self.status_line,
            urwid.AttrMap(self.search_edit, 'line_focus', 'line_focus'),
        ])

        self.item_list = urwid.SimpleListWalker(self.line_widgets)
        self.listbox = urwid.ListBox(self.item_list)

        self.view = urwid.Frame(body=self.listbox, footer=footer)

        self.loop = urwid.MainLoop(self.view, palette,
                event_loop=urwid.AsyncioEventLoop(),
                unhandled_input=self.on_unhandled_input)
        self.loop.screen.set_terminal_properties(colors=256)

        self.line_count_display.update(len(self.item_list), len(self.item_list))

        # TODO workaround, when update_list is called directly,
        # the linecount widget gets not updated
        self.loop.set_alarm_in(0.01, lambda *loop: self.update_list(''))

    def run(self):
        """Start main loop."""

        if self.infile.name == '<stdin>':
            # non-blocking but slower
            # pipe = self.loop.watch_pipe(self.update_lines)
            # process = subprocess.Popen(
            #     ["find", ".",  "-not", "-path", "*/\.*", "-type", "f"],
            #     stdout=pipe,
            #     stderr=subprocess.DEVNULL
            # )

            # blocking but faster
            pipe = subprocess.PIPE
            # process = subprocess.Popen(
            #     ["find", ".",  "-not", "-path", "*/\.*", "-type", "f"],
            #     stdout=pipe,
            #     stderr=subprocess.DEVNULL
            # )
            process = subprocess.Popen(["fd", "--type", "f"], stdout=pipe, stderr=subprocess.DEVNULL)
            stdout, stderr = process.communicate()
            self.update_lines(stdout)

        self.loop.run()

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
        try:
            lines = data.decode("UTF-8").split("\n")
        except AttributeError:
            pass

        # last line is whitespace, remove it
        last = lines.pop()

        for line in lines:
            # TODO: do this instead with 'find' parameters
            # remove directory indicator prefix if it exists
            if line[0:2] == "./":
                line = line.replace("./", "", 1)

            if line not in self.lines:
                self.lines.append(line)

        items = [LineItemWidget(item) for item in self.lines]

        self.item_list[:] = items
        self.line_count_display.update(total_lines=len(self.item_list))

    def update_list(self, search_text):
        if search_text == '' or search_text == '"' or search_text == '""':  # show all lines
            self.item_list[:] = [LineItemWidget(item) for item in self.lines]
            self.line_count_display.update(len(self.item_list))
        else:
            scored_lines = []
            for line in self.lines:
                score, match_positions = fuzzymatch_v1(line, search_text)
                scored_lines.append((line, score, match_positions))

            sorted_lines = sorted(scored_lines, key=lambda x: (x[1], len(x[0])), reverse=False)

            items = []
            for item in sorted_lines:
                if item[1] > 0:
                    if self.show_matches:
                        items.append(LineItemWidget(item[0], match_indices=item[2]))
                    else:
                        items.append(LineItemWidget(item[0]))

            if len(items) > 0:
                self.item_list[:] = items
                self.line_count_display.update(relevant_lines=len(self.item_list))
            else:
                self.item_list[:] = [urwid.Text(('empty_list', 'No selection'))]
                self.line_count_display.update(relevant_lines=0)

        try:
            self.item_list.set_focus(len(self.item_list)-1)
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

            self.view.set_footer(urwid.AttrMap(
                urwid.Text('selected: {}'.format(line)), 'foot'))

            self.inject_command(line)
            raise urwid.ExitMainLoop()

        elif input_ == 'tab':
            self.toggle_case_modifier()

        elif input_ == 'backspace':
            self.search_edit.set_edit_text(self.search_edit.get_text()[0][:-1])
            self.search_edit.set_edit_pos(len(self.search_edit.get_text()[0]))
            self.view.set_focus('footer')

        elif input_ == 'esc':
            raise urwid.ExitMainLoop()

        elif len(input_) == 1:  # ignore things like tab, enter
            self.search_edit.set_edit_text(self.search_edit.get_text()[0] + input_)
            self.search_edit.set_edit_pos(len(self.search_edit.get_text()[0]))
            self.view.set_focus('footer')

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

