#!/usr/bin/env python

import os
import sys
import stat
import subprocess
import struct
import fcntl
import termios

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.styles import Style

from matcher import fuzzymatch_v1


def walk_dir(command=None):
    command = command or ["fd", "--type", "f", "--hidden"]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    stdout, stderr = process.communicate()
    lines = stdout.decode("UTF-8").split("\n")

    # Remove trailing newline.
    lines = lines[0:-1]
    return lines


def load_data():
    """
    Read from stdin if input is from a pipe or file redirection.
    Otherwise, walk current working directory.
    """
    mode = os.fstat(sys.stdin.fileno()).st_mode
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        lines = sys.stdin.readlines()
    else:
        lines = walk_dir()
    return lines


def inject_command(command):
    command = (struct.pack('B', c) for c in os.fsencode(command))

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)

    # Disable echo.
    new[3] = new[3] & ~termios.ECHO

    termios.tcsetattr(fd, termios.TCSANOW, new)
    for c in command:
        fcntl.ioctl(fd, termios.TIOCSTI, c)
    termios.tcsetattr(fd, termios.TCSANOW, old)


class ResultBuffer:

    def __init__(self, sort=True, multi=False):
        self.sort = sort
        self.multi = multi

        self.lines = []

        # Lines matching the search pattern (score > 0) to show in buffer.
        self.relevant_lines = []

        self.selected_lines = []

        self.buffer = Buffer(
            multiline=True,
            read_only=True,
            document=Document("", 0),
            accept_handler=self._accept_handler,
        ) 

    @property
    def text(self):
        return self.buffer.text

    @property
    def document(self):
        return self.buffer.document

    def _accept_handler(self, buffer):
        if multi:
            line = " ".join(self.selected_lines)
        else:
            line = self.document.current_line
        inject_command(line)

    def set_lines(self, lines):
        self.lines = lines
        self.reset()

    def set_text(self, text):
        document = Document(text, len(text))
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
                    self.relevant_lines.append((line, score, match_positions))
            self.relevant_lines = sorted(
                self.relevant_lines,
                key=lambda x: (x[1], len(x[0])),
                reverse=False
            )
            rl_list = []
            for rl in self.relevant_lines:
                line, score, match_positions = rl
                rl_str = line + " - " + str(score) + " -  [" + " ,".join(str(i) for i in match_positions) + "]"
                rl_list.append(rl_str)
            text = "\n".join(rl_list)
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
        )

    def _accept_handler(self, buffer):
        if self.result_buffer.multi:
            line = " ".join(self.result_buffer.selected_lines)
        else:
            line = self.result_buffer.document.current_line
        inject_command(line)
        get_app().exit()

    def _on_text_changed(self, buffer):
        self.result_buffer.search(buffer.text)


class FuzzyFinder:

    def __init__(self):
        self.result_buffer = ResultBuffer(sort=True)
        self.prompt_buffer = PromptBuffer(self.result_buffer)

        self.layout = self._create_layout(reverse=False)
        self.key_bindings = self._create_key_bindings()
        self.style = self._create_style()
        self.application = self._create_application()

    def _create_key_bindings(self):
        key_bindings = KeyBindings()

        @key_bindings.add("escape")
        @key_bindings.add("c-c")
        @key_bindings.add("c-d")
        def exit_(event):
            event.app.exit()

        @key_bindings.add("up")
        @key_bindings.add("c-p")
        def cursor_up_(event):
            self.result_buffer.buffer.cursor_up()

        @key_bindings.add("down")
        @key_bindings.add("c-n")
        def cursor_down_(event):
            self.result_buffer.buffer.cursor_down()

        @key_bindings.add("tab")
        def select_(event):
            self.result_buffer.selected_lines.append(
                self.result_buffer.document.current_line
            )

        @key_bindings.add("s-tab")
        def unselect_(event):
            self.result_buffer.selected_lines.remove(
                self.result_buffer.document.current_line
            )

        return key_bindings

    def _create_style(self):
        style = Style.from_dict(
            {
                "result": "bg:#000044 #ffffff",
                "status": "reverse",
                "status.position": "#aaaa00",
                "status.key": "#ffaa00",
                "prompt": "bg:#000000 #ffffff",
            }
        )
        return style

    def _create_layout(self, reverse=False):
        def get_line_prefix(lineno, wrap_count):
            line = self.result_buffer.document.lines[lineno]
            if line in self.result_buffer.selected_lines: 
                return HTML("<style bg='ansired' fg='black'> </style>&gt;")
            else:
                return HTML("<style bg='ansired' fg='black'> </style> ")

        result_container = Window(
            BufferControl(
                buffer=self.result_buffer.buffer,
                focusable=True,
                focus_on_click=True,
            ),
            wrap_lines=False,
            cursorline=True,
            always_hide_cursor=False,
            style="class:result",
            get_line_prefix=get_line_prefix,
        )

        def get_statusbar_text():
            return [
                ("class:status", __file__ + " - "),
                (
                    "class:status.position",
                    "{}:{}".format(
                        self.result_buffer.document.cursor_position_row + 1,
                        self.result_buffer.document.cursor_position_col + 1,
                    ),
                ),
                ("class:status", " - "),
                (
                    "class:status.position",
                    "{}/{}".format(
                        len(self.result_buffer.relevant_lines),
                        len(self.result_buffer.lines),
                    ),
                ),
                ("class:status", " - Press "),
                ("class:status.key", "Ctrl-C"),
                ("class:status", " to exit, "),
                ("class:status.key", "/"),
                ("class:status", " for searching."),
            ]

        status_container = Window(
            content=FormattedTextControl(get_statusbar_text),
            height=D.exact(1),
            dont_extend_height=True,
            wrap_lines=False,
            style="class:status",
        )

        prompt_container = Window(
            BufferControl(
                buffer=self.prompt_buffer.buffer,
                focusable=True,
                focus_on_click=True,
            ),
            height=1,
            dont_extend_height=True,
            wrap_lines=False,
            style="class:prompt",
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
            style=self.style,
            mouse_support=True,
            full_screen=True,
            enable_page_navigation_bindings=False,
        )
        return application

    def _pre_run(self):
        lines = load_data()
        self.result_buffer.set_lines(lines)

    def run(self):
        """Start the event loop."""
        self.application.run(pre_run=self._pre_run)


def main():
    FuzzyFinder().run()


if __name__ == "__main__":
    main()
