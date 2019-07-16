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
        urwid.connect_signal(self.prompt, 'change', self._on_prompt_change)

        self._update_list(self.lines)


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


    def _on_prompt_change(self, prompt, new_pattern):
        self.list_walker.clear()

        # display all lines if prompt is empty
        if new_pattern == "":
            self._update_list(self.lines)
            self._update_status_line(len(self.lines), len(self.lines))
        else:
            matches = 0
            scored_lines = self.matcher.compute_scores(new_pattern)
            for line, score, match_positions in scored_lines:
                if score > 0:
                    self.list_walker.append(urwid.Text(line))
                    matches += 1
                    # self.body.set_focus(len(self.list_walker) - 1, 'above')

            self._update_status_line(matches, len(self.lines))

