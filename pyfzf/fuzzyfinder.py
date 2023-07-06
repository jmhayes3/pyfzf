#!/usr/bin/env python

import os
import sys
import stat
import subprocess
import struct
import fcntl
import termios
import cProfile

from prompt_toolkit import print_formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.layout.containers import Window, HSplit, ScrollOffsets
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.screen import Screen, Char, _CHAR_CACHE
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.styles import Style
from prompt_toolkit.data_structures import Point

from matcher import FuzzyMatch
from key_bindings import create_key_bindings
from layout import create_layout
from helpers import profile, timeit


# Tiny modification to prompt_toolkit cursorline to get desired styling.
# This could probably be done a better way but idk...
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


def run_command(command=None):
    """
    Run command in a subprocess and return the output as
    a list of strings.
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


def load_initial_input():
    """
    Read from stdin if input is from a pipe or file redirection, otherwise, run
    shell command to get input.
    """
    mode = os.fstat(sys.stdin.fileno()).st_mode
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        lines = sys.stdin.read().splitlines()
        sys.stdin = sys.stdout  # Necessary to work with prompt_toolkit
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


class Finder:

    def __init__(self, matcher, lines, **kwargs):
        self.matcher = matcher
        self.input_lines = lines[:]
        self.matched_lines = lines

        self.selected_lines = set()

        self.prev_pattern = ""

        self.with_pos = True
        self.multi = True
        self.sort = True
        self.reverse = False
        self.height = None

        if "with_pos" in kwargs.keys():
            self.with_pos = kwargs.get("with_pos")
        if "sort" in kwargs.keys():
            self.sort = kwargs.get("sort")
        if "multi" in kwargs.keys():
            self.multi = kwargs.get("multi")
        if "reverse" in kwargs.keys():
            self.reverse = kwargs.get("reverse")
        if "height" in kwargs.keys():
            self.height = kwargs.get("height")

        self.result_buffer=Buffer(
            name="result",
            multiline=True,
            read_only=False,
            document=Document("", 0),
        )

        self.prompt_buffer=Buffer(
            name="prompt",
            multiline=False,
            read_only=False,
            accept_handler=self.on_accept,
            on_text_insert=self.on_pattern_insert,
            on_text_changed=self.on_pattern_changed,
        )

        self.layout = create_layout(self)

        self.application = Application(
            layout=self.layout,
            key_bindings=create_key_bindings(self),
            mouse_support=True,
            full_screen=False,
            enable_page_navigation_bindings=False,
            # max_render_postpone_time=0
        )

        # show initial input in result buffer
        self.set_result(self.input_lines)

    def set_result(self, lines):
        text = "\n".join(lines)
        if self.reverse:
            cur_pos = 0
        else:
            cur_pos = len(text)
        self.result_buffer.set_document(Document(text, cur_pos))

    def get_result_prefix(self, lineno, wrap_count):
        line = self.result_buffer.document.lines[lineno]
        if line in self.selected_lines:
            prefix = " >"
        else:
            prefix = "  "
        return FormattedText([("", ""), ("ansired", prefix),])

    def get_statusbar_text(self):
        text = "{}/{}".format(len(self.matched_lines), len(self.input_lines))
        if self.selected_lines:
            text += " ({})".format(len(self.selected_lines))
        return FormattedText([("ansiyellow", text)])

    def on_accept(self, buffer):
        if self.multi:
            line = " ".join(self.selected_lines)
        else:
            line = self.result_buffer.document.current_line
        inject_line(line)
        self.application.exit()

    def on_pattern_insert(self, buffer):
        result = self.find_matches(self.input_lines, buffer.text)
        self.set_result(result)
        self.prev_pattern = buffer.text

    def preprocess(self, line, pattern):
        for p in pattern:
            if p in line:
                continue
            else:
                return None
        return line

    def on_pattern_changed(self, buffer):
        if len(buffer.text) < len(self.prev_pattern):
            result = self.find_matches(self.input_lines, buffer.text)
            self.set_result(result)
            self.prev_pattern = buffer.text
        else:
            self.set_result(self.input_lines)

    def find_matches(self, lines, pattern):
        matched_lines = []
        for line in lines:
            if self.preprocess(line, pattern):
                score, match_positions = self.matcher.process(line, pattern)
                if score > 0:
                    matched_lines.append((line, score, match_positions))
        if self.sort:
            # sort by score, line length
            matched_lines = sorted(
                matched_lines,
                key=lambda line: (line[1], len(line[0])),
                reverse=False
            )
        self.matched_lines = matched_lines
        return [line[0] for line in matched_lines]

    def run(self):
        self.application.run()


# @profile()
def main():
    lines = load_initial_input()
    matcher = FuzzyMatch(with_pos=True)
    Finder(matcher, lines).run()


if __name__ == "__main__":
    main()
