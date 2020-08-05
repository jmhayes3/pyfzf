#!/usr/bin/env python

import os
import sys
import stat
import subprocess
import struct
import fcntl
import termios
import string
import cProfile

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.containers import Window, HSplit, ScrollOffsets
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.screen import Screen, Char, _CHAR_CACHE
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.styles import Style
from prompt_toolkit.data_structures import Point

from matcher import fuzzymatch_v1
from processors import MatchProcessor
from helpers import profile, timeit


def _highlight_cursorlines(
        self, new_screen: Screen, cpos: Point, x: int, y: int, width: int, height: int
    ) -> None:
        """
        Highlight cursor row/column.
        """
        cursor_line_style = " bold "
        cursor_column_style = " class:cursor-column "

        data_buffer = new_screen.data_buffer

        # Highlight cursor line.
        if self.cursorline():
            row = data_buffer[cpos.y]
            for x in range(x, x + width):
                original_char = row[x]
                row[x] = _CHAR_CACHE[
                    original_char.char, cursor_line_style
                ]

        # Highlight cursor column.
        if self.cursorcolumn():
            for y2 in range(y, y + height):
                row = data_buffer[y2]
                original_char = row[cpos.x]
                row[cpos.x] = _CHAR_CACHE[
                    original_char.char, original_char.style + cursor_column_style
                ]

        # Highlight color columns
        colorcolumns = self.colorcolumns
        if callable(colorcolumns):
            colorcolumns = colorcolumns()

        for cc in colorcolumns:
            assert isinstance(cc, ColorColumn)
            column = cc.position

            if column < x + width:  # Only draw when visible.
                color_column_style = " " + cc.style

                for y2 in range(y, y + height):
                    row = data_buffer[y2]
                    original_char = row[column + x]
                    row[column + x] = _CHAR_CACHE[
                        original_char.char, original_char.style + color_column_style
                    ]

Window._highlight_cursorlines = _highlight_cursorlines

class MatchedLine:

    def __init__(self, line, score, match_positions):
        self.line = line
        self.score = score
        self.match_positions = match_positions


def run_command(command=None):
    """
    Run the given command in a subprocess and return the output delimited by
    line as a list of strings.
    """
    # command = command or ["fd", "--type", "f"]
    command = command or ["fd", "--type", "f", "--hidden"]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    stdout, stderr = process.communicate()
    lines = stdout.decode("UTF-8").splitlines()
    return lines


def load_lines():
    """
    Read from stdin if input is from a pipe or file redirection.
    Otherwise, run shell command to get input.
    """
    mode = os.fstat(sys.stdin.fileno()).st_mode
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        lines = sys.stdin.read().splitlines()
        sys.stdin = sys.stdout
    else:
        lines = run_command()
    return lines


def inject_line(line):
    """
    Copy the given line to the terminal.
    """
    line = (struct.pack('B', c) for c in os.fsencode(line))

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)

    # Disable echo.
    new[3] = new[3] & ~termios.ECHO

    termios.tcsetattr(fd, termios.TCSANOW, new)
    for c in line:
        fcntl.ioctl(fd, termios.TIOCSTI, c)

    termios.tcsetattr(fd, termios.TCSANOW, old)


class ResultBuffer:

    def __init__(self, matcher=None, sort=True, multi=True, reverse=False):
        self.sort = sort
        self.multi = multi
        self.reverse = reverse

        self.lines = []

        self.relevant_lines = []

        self.selected_lines = set()

        self.buffer = Buffer(
            multiline=True,
            read_only=True,
            document=Document("", 0),
        )

    @property
    def text(self):
        return self.buffer.text

    @property
    def document(self):
        return self.buffer.document

    def set_lines(self, lines):
        self.lines = lines
        self.reset()

    def set_text(self, text):
        if self.reverse:
            cur_pos = 0
        else:
            cur_pos = len(text)
        document = Document(text, cur_pos)
        self.buffer.set_document(document, bypass_readonly=True)

    def reset(self):
        text = "\n".join(self.lines)
        self.set_text(text)

    def search(self, pattern):
        self.relevant_lines.clear()
        if pattern:
            for index, line in enumerate(self.lines):
                score, match_positions = fuzzymatch_v1(line, pattern)
                if score > 0:
                    self.relevant_lines.append(
                        MatchedLine(line, score, match_positions)
                    )
            if self.sort:
                # Sort by score, then line length.
                self.relevant_lines = sorted(
                    self.relevant_lines,
                    key=lambda line: (line.score, len(line.line)),
                    reverse=False
                )
            lines = [line.line for line in self.relevant_lines]
            text = "\n".join(lines)
            self.set_text(text)
        else:
            self.reset()


class PromptBuffer:

    def __init__(self, result_buffer):
        self.result_buffer = result_buffer

        self.buffer = Buffer(
            multiline=False,
            read_only=False,
            accept_handler=self._accept_handler,
            on_text_changed=self._on_text_changed,
            on_cursor_position_changed=self._on_cursor_position_changed
        )

    def _accept_handler(self, buffer):
        app = get_app()
        if self.result_buffer.multi:
            line = " ".join(self.result_buffer.selected_lines)
        else:
            line = self.result_buffer.document.current_line
        inject_line(line)
        app.exit()

    def _on_text_changed(self, buffer):
        self.result_buffer.search(buffer.text)

    def _on_cursor_position_changed(self, buffer):
        pass


class FuzzyFinder:

    def __init__(self, lines, sort=True, multi=True, reverse=False, **kwargs):
        self.lines = lines
        self.multi = multi
        self.sort = sort
        self.reverse = reverse
        self.height = None

        if "height" in kwargs.keys():
            self.height = kwargs.get("height")

        self.result_buffer = ResultBuffer(
            sort=self.sort,
            multi=self.multi,
            reverse=self.reverse
        )
        self.result_buffer.set_lines(self.lines)

        self.prompt_buffer = PromptBuffer(self.result_buffer)

        self.layout = self._create_layout(reverse=self.reverse)
        self.key_bindings = self._create_key_bindings()
        self.application = self._create_application()

    def _create_key_bindings(self):
        key_bindings = KeyBindings()

        @Condition
        def is_multi():
            return self.result_buffer.multi

        @key_bindings.add("escape")
        @key_bindings.add("c-c")
        @key_bindings.add("c-d")
        def exit_(event):
            event.app.exit()

        @key_bindings.add("up", eager=True)
        @key_bindings.add("c-p", eager=True)
        def cursor_up_(event):
            self.result_buffer.buffer.cursor_up()

        @key_bindings.add("down", eager=True)
        @key_bindings.add("c-n", eager=True)
        def cursor_down_(event):
            self.result_buffer.buffer.cursor_down()

        @key_bindings.add("tab", filter=is_multi)
        def select_(event):
            self.result_buffer.selected_lines.add(
                self.result_buffer.document.current_line
            )

        @key_bindings.add("s-tab", filter=is_multi)
        def unselect_(event):
            self.result_buffer.selected_lines.remove(
                self.result_buffer.document.current_line
            )

        # @key_bindings.add(Keys.ScrollUp)
        # def su_(event):
        #     self.result_buffer.buffer.cursor_up()

        # @key_bindings.add(Keys.ScrollDown)
        # def sd_(event):
        #     self.result_buffer.buffer.cursor_down()

        @key_bindings.add(Keys.Vt100MouseEvent)
        def mouse_event_(event):
            mouse_event = event.key_sequence[0].data
            if "[<0;" in mouse_event:
                # click
                # get_app().layout.focus_last()
                pass
            elif "[<64;" in mouse_event:
                # scroll up
                self.result_buffer.buffer.cursor_up()
            elif "[<65;" in mouse_event:
                # scroll down
                self.result_buffer.buffer.cursor_down()

        return key_bindings

    def _create_layout(self, reverse=False):
        def get_line_prefix(lineno, wrap_count):
            prefix = " "
            # if lineno is self.result_buffer.document.cursor_position_row:
            #     prefix = "<ansired>&gt;</ansired>"
            line = self.result_buffer.document.lines[lineno]
            selected = " "
            if line in self.result_buffer.selected_lines:
                selected = "<b><ansired>&gt;</ansired></b>"
            return HTML(prefix + selected)

        result_container = Window(
            BufferControl(
                buffer=self.result_buffer.buffer,
                focusable=False,
                focus_on_click=True,
                input_processors=[
                    MatchProcessor(self.result_buffer),
                ],
            ),
            height=D(min=1, max=self.height),
            dont_extend_height=False,
            wrap_lines=False,
            always_hide_cursor=True,
            cursorline=True,
            get_line_prefix=get_line_prefix,
        )

        def get_statusbar_text():
            if len(self.result_buffer.selected_lines) > 0:
                return HTML("  <ansiyellow>{}/{} ({})</ansiyellow>".format(
                        len(self.result_buffer.relevant_lines),
                        len(self.result_buffer.lines),
                        len(self.result_buffer.selected_lines)
                    )
                )
            else:
                return HTML("  <ansiyellow>{}/{}</ansiyellow>".format(
                        len(self.result_buffer.relevant_lines),
                        len(self.result_buffer.lines)
                    )
                )

        status_container = Window(
            content=FormattedTextControl(get_statusbar_text),
            height=D.exact(1),
            dont_extend_height=True,
            wrap_lines=False,
        )

        prompt_container = Window(
            BufferControl(
                buffer=self.prompt_buffer.buffer,
                focusable=True,
                focus_on_click=True,
                include_default_input_processors=False,
            ),
            height=D.exact(1),
            dont_extend_height=True,
            wrap_lines=False,
            get_line_prefix=lambda lineno, wrap_count: HTML("<b>> </b>"),
        )

        if reverse:
            root_container = HSplit([
                prompt_container,
                status_container,
                result_container,
            ])
        else:
            root_container = HSplit([
                result_container,
                status_container,
                prompt_container,
            ])

        return Layout(root_container, focused_element=prompt_container)

    def _create_application(self):
        application = Application(
            layout=self.layout,
            key_bindings=self.key_bindings,
            mouse_support=True,
            full_screen=False,
            enable_page_navigation_bindings=False,
            max_render_postpone_time=0
        )
        return application

    def run(self):
        self.application.run()


@profile()
def main():
    lines = load_lines()
    ff = FuzzyFinder(
        sort=False,
        multi=True,
        reverse=True,
        lines=lines
    )
    ff.run()


if __name__ == "__main__":
    main()
