#!/usr/bin/env python

"""
Python implementation of fzf.
"""

import os
import sys
import stat
import argparse
import logging
import threading
import time

from enum import Enum
from queue import PriorityQueue, Queue

import urwid

from util import print_matrix, initialize_matrix, get_files_and_dirs


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)-4s %(threadName)s %(message)s",
    datefmt="%H:%M:%S",
    filename="trace.log",
)


def get_parser():
    parser = argparse.ArgumentParser(description="Command-line fuzzy finder")
    parser.add_argument("-p", help="the pattern to match input against")
    parser.add_argument("-f", help="file to use as input for fuzzy matching")
    parser.add_argument("--algo", help="algorithm to use for fuzzy matching")

    return parser


def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())

    if args["f"]:
        input_file = args["f"]
        if os.path.isfile(input_file):
            with open(input_file, "r") as f:
                lines = f.readlines()
        else:
            print("File does not exist.")
    else:
        mode = os.fstat(sys.stdin.fileno()).st_mode

        # If stdin is from a pipe or file redirection, process input.
        # Otherwise, walk current dir and use file/dir listing as input.
        if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
            print("PIPE or FILE REDIRECTION, processing input.")
            lines = sys.stdin.readlines()
        else:
            print("No PIPE or FILE REDIRECTION, walking cwd.")
            lines = get_files_and_dirs()

    return lines


SCORE_MATCH = 16
SCORE_GAP_START = -3
SCORE_GAP_EXTENSION = -1
BONUS_BOUNDARY = SCORE_MATCH / 2
BONUS_NON_ALNUM = SCORE_MATCH / 2
BONUS_CAMEL_123 = BONUS_BOUNDARY + SCORE_GAP_EXTENSION
BONUS_CONSECUTIVE = -(SCORE_GAP_START + SCORE_GAP_EXTENSION)
BONUS_FIRST_CHAR_MULTIPLIER = 2

LOWER = 1
UPPER = 2
NUMBER = 3
NON_ALNUM = 4


class Matcher:

    def __init__(self, lines, msg_queue):
        self.lines = lines
        self.msg_queue = msg_queue


    # charClassOf implementation
    def get_char_type(self, char):
        if char.isalnum():
            if char.islower():
                return LOWER
            elif char.isupper():
                return UPPER
            else:
                return NUMBER
        else:
            return NON_ALNUM


    # bonusFor implementation
    def calc_bonus(self, prev, curr):
        if prev is NON_ALNUM and curr is not NON_ALNUM:
            return BONUS_BOUNDARY
        elif prev is LOWER and curr is UPPER:
            return BONUS_CAMEL_123
        elif prev is not NUMBER and curr is NUMBER:
            return BONUS_CAMEL_123
        elif curr is NON_ALNUM:
            return BONUS_NON_ALNUM
        else:
            return 0


    def normalize(self, chars):
        """Normalize latin script letters."""
        pass


    # if backtrack is False, don't traverse backwards to find shorter match
    def get_score(self, chars, pattern, backtrack=True):
        c_length = len(chars)
        p_length = len(pattern)

        # +1 for gap row and gap column
        rows = c_length + 1
        cols = p_length + 1
        score_matrix = initialize_matrix(rows, cols)

        p_idx = 0
        in_gap = False
        consecutive = 0
        first_bonus = 0
        prev_char_type = NON_ALNUM

        score = 0
        max_score = 0
        max_score_pos = (0, 0)
        match_positions = []
        for c_idx in range(0, c_length):
            if consecutive > 0:
                p_idx += 1
            if p_idx < p_length:
                c = chars[c_idx]
                curr_char_type = self.get_char_type(c)
                if c == pattern[p_idx]:
                    score += SCORE_MATCH
                    bonus = self.calc_bonus(prev_char_type, curr_char_type)
                    if consecutive == 0:
                        first_bonus = bonus
                    else:
                        if bonus == BONUS_BOUNDARY:
                            first_bonus = bonus
                            bonus = max(bonus, BONUS_CONSECUTIVE)
                        else:
                            bonus = max(bonus, first_bonus, BONUS_CONSECUTIVE)
                    if c == pattern[0]:
                        score += (bonus * BONUS_FIRST_CHAR_MULTIPLIER)
                    else:
                        score += bonus
                    in_gap = False
                    consecutive += 1
                    match_positions.append(c_idx)
                else:
                    if in_gap:
                        score += SCORE_GAP_EXTENSION
                    else:
                        score += SCORE_GAP_START
                    in_gap = True
                    consecutive = 0
                    first_bonus = 0

                score_matrix[c_idx + 1][p_idx + 1] = score
                prev_char_type = curr_char_type

                if score > max_score:
                    max_score = score
                    max_score_pos = (c_idx + 1, p_idx + 1)
            else:
                break

        # if all pattern characters aren't found, return None
        if p_length >= p_idx + 1:
            return score_matrix, 0, []
        elif backtrack:
            return self.backtrace(chars, pattern, max_score_pos)
        else:
            return score_matrix, max_score, match_positions


    def backtrace(self, chars, pattern, start_pos):
        c_length = len(chars)
        p_length = len(pattern)

        # +1 for gap row and gap column
        rows = c_length + 1
        cols = p_length + 1
        score_matrix = initialize_matrix(rows, cols)

        in_gap = False
        consecutive = 0
        first_bonus = 0
        prev_char_type = NON_ALNUM

        score = 0
        max_score = 0
        start_c_idx, p_idx = start_pos
        p_idx = p_idx - 1
        match_positions = []
        for c_idx in range(start_c_idx - 1, -1, -1):
            if consecutive > 0:
                p_idx -= 1
            if p_idx >= 0:
                c = chars[c_idx]
                curr_char_type = self.get_char_type(c)
                if c == pattern[p_idx]:
                    score += SCORE_MATCH
                    bonus = self.calc_bonus(prev_char_type, curr_char_type)
                    if consecutive == 0:
                        first_bonus = bonus
                    else:
                        if bonus == BONUS_BOUNDARY:
                            first_bonus = bonus
                            bonus = max(bonus, BONUS_CONSECUTIVE)
                        else:
                            bonus = max(bonus, first_bonus, BONUS_CONSECUTIVE)
                    if c == pattern[0]:
                        score += (bonus * BONUS_FIRST_CHAR_MULTIPLIER)
                    else:
                        score += bonus
                    in_gap = False
                    consecutive += 1
                    match_positions.append(c_idx)
                else:
                    if in_gap:
                        score += SCORE_GAP_EXTENSION
                    else:
                        score += SCORE_GAP_START
                    in_gap = True
                    consecutive = 0
                    first_bonus = 0

                score_matrix[c_idx + 1][p_idx + 1] = score
                prev_char_type = curr_char_type

                if score > max_score:
                    max_score = score
            else:
                break

        return score_matrix, max_score, match_positions


    # fuzzy_match makes two assumptions
    # 1. "pattern" is given in lowercase if "case_sensitive" is false
    # 2. "pattern" is already normalized if "normalize" is true
    def fuzzymatch_v1(self, chars, pattern, case=True, normalize=True, with_pos=True):
        score_matrix, max_score, match_positions = self.get_score(chars, pattern)
        if with_pos:
            return max_score, match_positions
        else:
            return max_score


    def compute_scores(self, pattern):
        processed = []
        for index, line in enumerate(self.lines):
            line = line.rstrip("\n")
            score, match_positions = self.fuzzymatch_v1(line, pattern)
            processed.append((index, score, match_positions))
        return processed


class Tui:
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

    def __init__(self, lines, msg_queue):
        # Frame header
        # self.header_text = urwid.Text('pyfzf')
        # self.header = urwid.AttrMap(self.header_text, 'head')

        # Frame body
        self.walker = urwid.SimpleFocusListWalker([])

        for line in lines:
            self.walker.append(urwid.Text(line))

        self.body = urwid.ListBox(self.walker)

        # Frame footer
        self.initial_length = str(len(lines))
        self.status_line = urwid.Text(("foot", self.initial_length + "/" + self.initial_length))
        self.prompt = urwid.Edit(("> "))
        self.footer = urwid.Pile([self.status_line, self.prompt])

        # assemble Frame
        self.layout = urwid.Frame(body=self.body, footer=self.footer, focus_part="footer")

        self.screen = urwid.raw_display.Screen()

        self.loop = urwid.MainLoop(self.layout, self.palette,
            unhandled_input=self._unhandled_input, screen=self.screen)

        urwid.connect_signal(self.prompt, 'change', self._on_prompt_change)

        self.lines = lines
        self.msg_queue = msg_queue

        self.matcher = Matcher(self.lines, self.msg_queue)

        # self._check_queue(self.loop, None)

    def _unhandled_input(self, k):
        if k in ('q','Q'):
            raise urwid.ExitMainLoop()

    def _on_prompt_change(self, prompt, new_pattern):
        self.walker.clear()
        scored_lines = self.matcher.compute_scores(new_pattern)
        for index, score, match_positions in scored_lines:
            line = self.lines[index]
            if score > 0:
                self.walker.append(urwid.Text(line))
                # self.body.set_focus(len(self.walker) - 1, 'above')

    def _check_queue(self, loop, *args):
        pass
        # loop.set_alarm_in(sec=0.01, callback=self._check_queue)

        # if not self.msg_queue.empty():
        #     msg = self.msg_queue.get_nowait()
        # else:
        #     return

        # index, score, match_positions = msg

        # if score > 0:
        #     line = self.lines[index]
        # else:
        #     return

        # self.walker.append(urwid.Text(('body', line)))
        # self.body.set_focus(len(self.walker) - 1, 'above')


def updater(stop_event, msg_queue):
    logging.info("start")
    while not stop_event.wait(timeout=1.0):
        msg_queue.put("test")
    logging.info("stop")


def main():
    lines = command_line_runner()

    # stop_ev = threading.Event()
    msg_q = Queue()

    # threading.Thread(
    #     target=updater, args=[stop_ev, msg_q],
    #     name="updater",
    # ).start()

    # logging.info("start")
    Tui(lines, msg_q).loop.run()
    # logging.info("stop")

    # after interface exits, signal threads to exit, wait for them
    # logging.info("stopping threads")

    # stop_ev.set()
    # for th in threading.enumerate():
    #     if th != threading.current_thread():
    #         th.join()


if __name__ == '__main__':
    main()

