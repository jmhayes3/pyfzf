import os
import sys
import subprocess
import re
import logging

import urwid


class Interface:

    palette = [
        ('body', 'white', 'black'),
        ('flagged', 'black', 'dark green', ('bold','underline')),
        ('focus', 'light gray', 'dark blue'),
        ('flagged focus', 'yellow', 'dark cyan',
                ('bold','standout','underline')),
        ('head', 'yellow', 'black', 'standout'),
        ('foot', 'light gray', 'black'),
        ('key', 'light cyan', 'black','underline'),
        ('title', 'white', 'black', 'bold'),
        ('dirmark', 'black', 'dark cyan', 'bold'),
        ('flag', 'dark gray', 'light gray'),
        ('error', 'dark red', 'light gray'),
    ]


    def __init__(self, matcher, lines=[]):
        # Frame header
        # self.header_text = urwid.Text('pyfzf')
        # self.header = urwid.AttrMap(self.header_text, 'head')

        self.lines = lines

        self.matcher = matcher

        self.list_walker = urwid.SimpleFocusListWalker([])

        self.body = urwid.ListBox(self.list_walker)

        # Frame footer
        self.status_line = urwid.Text(
            ("foot", "{0}/{1}".format(len(self.lines), len(self.lines)))
        )
        self.prompt = urwid.Edit(("> "))
        self.footer = urwid.Pile([self.status_line, self.prompt])

        # assemble Frame
        self.layout = urwid.Frame(
            body=self.body,
            footer=self.footer,
            focus_part="footer"
        )

        self.screen = urwid.raw_display.Screen()
        self.loop = urwid.MainLoop(self.layout, self.palette,
            unhandled_input=self._unhandled_input, screen=self.screen)

        urwid.connect_signal(self.prompt, 'change', self._prompt_handler)

        self.prev = ""


    def run(self):
        """Spawn subprocess to get file listing and start event loop."""

        pipe = self._get_pipe(self.new_line_handler)
        process = subprocess.Popen(
            ["find", ".",  "-not", "-path", "*/\.*", "-type", "f"],
            stdout=pipe,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )
        self.loop.run()
        process.kill()


    def _get_pipe(self, handler):
        return self.loop.watch_pipe(handler)


    def get_pipe(self, handler):
        if handler == "new_line_handler":
            return self.loop.watch_pipe(self.new_line_handler)
        elif handler == "new_match_handler":
            return self.loop.watch_pipe(self.new_match_handler)
        else:
            raise ValueError


    def _unhandled_input(self, k):
        if k in ('q','Q'):
            raise urwid.ExitMainLoop()


    def _append_line(self, line):
        self.lines.append(line)


    # TODO: add optional arg that accepts a list of match positions to colorize
    def _update_list(self, lines):
        for line in lines:
            self.list_walker.append(urwid.Text(line))


    def _update_status_line(self, num_of_matches, num_of_lines):
        self.status_line.set_text(
            ("foot", "{0}/{1}".format(num_of_matches, num_of_lines))
        )


    def _extract_text(self):
        lines = []
        for line in self.list_walker:
            line = line.get_text()[0]
            lines.append(line)
        return lines


    def _prompt_handler(self, prompt, new_pattern):
        # self.list_walker.clear()

        # display all lines if prompt is empty
        if new_pattern == "":
            self.list_walker.clear()
            self._update_list(self.lines)
            self._update_status_line(len(self.lines), len(self.lines))
        else:
            current_lines = self._extract_text()
            self.spawn_matcher(new_pattern, current_lines)
            # matches = 0
            # scored_lines = self.matcher.compute_scores(new_pattern)
            # for line, score, match_positions in scored_lines:
            #     if score > 0:
            #         self.list_walker.append(urwid.Text(line))
            #         matches += 1
            #         # self.body.set_focus(len(self.list_walker) - 1, 'above')

            # self._update_status_line(matches, len(self.lines))


    # TODO: run as thread instead of subprocess?
    def spawn_matcher(self, pattern, lines):
        lines = "\n".join(lines)
        pipe = self.get_pipe("new_match_handler")
        path_to_exec = os.path.join(os.path.dirname(sys.argv[0]), "matcher.py")
        process = subprocess.Popen(
            ["python", "-u", path_to_exec, str(pattern), lines],
            stdout=pipe,
            close_fds=True
        )


    def new_line_handler(self, data):
        out = data.decode("UTF-8").split("\n")

        # TODO: avoid this by using appropriate params when spawning subprocess
        # remove empty str item from list
        # remove current dir indicator (".") if it is present
        if out[0] == ".":
            out = out[1:-1]
        else:
            out = out[0:-1]

        for line in out:
            line = line.replace("./", "", 1)
            self.lines.append(line)
            self.list_walker.append(urwid.Text(line))

        self._update_status_line(len(self.list_walker), len(self.lines))


    def new_match_handler(self, data):
        logging.debug("--Beginning of function--")
        logging.debug("NUM OF LINES: " + str(len(data)))

        data = data.decode("UTF-8").split("\n")

        pattern = "LINE: .+ SCORE: .+ MATCHES: \[.?\]"
        regex = re.compile("({})".format(pattern), re.DOTALL)

        logging.debug("Start loop.")
        for chunk in data:
            logging.debug("PREV: " + self.prev)
            logging.debug("CHUNK: " + chunk)
            match = regex.match(self.prev + chunk)
            if match:
                logging.debug("MATCH: " + match.group(0))
            else:
                logging.debug("NO MATCH.")
                self.prev = chunk

        logging.debug("End loop.")
        logging.debug("--End of function--")


