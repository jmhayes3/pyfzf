import os
import sys
import subprocess
import re
import logging
import concurrent.futures

import urwid

from matcher import compute_scores


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


    def __init__(self):
        # Frame header
        # self.header_text = urwid.Text('pyfzf')
        # self.header = urwid.AttrMap(self.header_text, 'head')

        self.lines = []

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

        self.loop = urwid.MainLoop(
            self.layout,
            self.palette,
            unhandled_input=self._unhandled_input,
            screen=self.screen
        )

        urwid.connect_signal(self.prompt, "change", self._prompt_handler)

        self.prev = ""

        self.current_pattern = ""


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


    def _unhandled_input(self, k):
        if k in ('q','Q'):
            raise urwid.ExitMainLoop()


    def _append_line(self, line):
        self.lines.append(line)


    def _append_list(self, line):
        self.list_walker.append(urwid.Text(line))


    # TODO: add optional arg that accepts a list of match positions to colorize
    def _extend_list(self, lines):
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


    # TODO: handle case where pattern length is reduced (last used pattern)
    def _prompt_handler(self, prompt, new_pattern):
        # display all lines if prompt is empty
        if new_pattern == "":
            self.list_walker.clear()
            self._extend_list(self.lines)
            self._update_status_line(len(self.lines), len(self.lines))
        elif len(new_pattern) < len(self.current_pattern):
            current_lines = self.lines
            pipe = self._get_pipe(self.new_match_handler)
            with concurrent.futures.ProcessPoolExecutor() as executor:
                result = executor.submit(compute_scores, new_pattern, current_lines, fd=pipe)
            self.list_walker.clear()
        else:
            current_lines = self._extract_text()
            pipe = self._get_pipe(self.new_match_handler)
            with concurrent.futures.ProcessPoolExecutor() as executor:
                # result = executor.submit(compute_scores, new_pattern, current_lines)
                result = executor.submit(compute_scores, new_pattern, current_lines, fd=pipe)
            # self.spawn_matcher_as_subprocess(new_pattern, current_lines)
            self.list_walker.clear()

        self.current_pattern = new_pattern


    # TODO: run as thread instead of subprocess?
    # won't work on large inputs due to limitation on num of args
    def spawn_matcher_as_subprocess(self, pattern, lines):
        lines = "\n".join(lines)
        pipe = self._get_pipe(self.new_match_handler)
        path_to_exec = os.path.join(os.path.dirname(sys.argv[0]), "matcher.py")
        process = subprocess.Popen(
            ["python", "-u", path_to_exec, str(pattern), lines],
            stdout=pipe,
            close_fds=True
        )


    def spawn_matcher_as_thread(self, pattern, lines):
        pipe = self._get_pipe(self.new_match_handler)


    def new_line_handler(self, data):
        out = data.decode("UTF-8").split("\n")

        # don't include last item in list as it is empty
        out = out[0:-1]

        for line in out:
            line = line.replace("./", "", 1)
            self.lines.append(line)
            self.list_walker.append(urwid.Text(line))

        self._update_status_line(len(self.list_walker), len(self.lines))


    def new_match_handler(self, data):
        logging.debug("--Beginning of function--")

        data = data.decode("UTF-8").split("\n")

        logging.debug("NUM OF LINES: " + str(len(data)))

        pattern = "LINE: .+; SCORE: .+; MATCHES: \[.*\];"
        regex = re.compile("({})".format(pattern), re.DOTALL)

        logging.debug("Start loop.")
        for chunk in data:
            logging.debug("PREV: " + self.prev)
            logging.debug("CHUNK: " + chunk)
            match = regex.match(self.prev + chunk)
            if match:
                logging.debug("MATCH: " + match.group(0))
                new_match = match.group(0)
                self.process_new_match(new_match)
            else:
                logging.debug("NO MATCH.")
                self.prev = chunk

        logging.debug("End loop.")
        logging.debug("--End of function--")


    def process_new_match(self, match):
        # print(match)
        match = match.split(";")[0:-1]
        line = match[0].strip("LINE: ")
        score = match[1].strip("SCORE: ")
        matches = match[2].strip(" MATCHES: []")
        # print(line)
        # print(score)

        match_pos = []
        if len(matches) > 0:
            m_pos = matches.split(",")
            for i in m_pos:
                pos = int(i)
                match_pos.append(pos)

        # print(match_pos)

        if isinstance(score, str):
            score = float(score)

        if score > 0:
            self._append_list(line)
            self._update_status_line(len(self.list_walker), len(self.lines))

