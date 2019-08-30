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
import subprocess
import urwid
import cProfile

from interface import Interface
from matcher import compute_scores


def get_parser():
    parser = argparse.ArgumentParser(description="Command-line fuzzy finder")
    parser.add_argument("--algo", help="Algorithm to use for fuzzy matching")

    return parser


# TODO: add support for specifying alternate find commands
def get_files_and_dirs(include_dirs=False, include_hidden=False, pipe=subprocess.PIPE):
    # recursively get all files, ignoring hidden files (-not -path '*/\.*)
    if include_dirs:
        if include_hidden:
            process = subprocess.Popen(["find", "."], stdout=pipe)
        else:
            process = subprocess.Popen(["find", ".",  "-not", "-path", "*/\.*"], stdout=pipe)
    else:
        if include_hidden:
            process = subprocess.Popen(["find", ".", "-type", "f"], stdout=pipe)
        else:
            process = subprocess.Popen(["find", ".",  "-not", "-path", "*/\.*", "-type", "f"], stdout=pipe)

    # communicate method is blocking
    out, err = process.communicate()
    out = out.decode("UTF-8").split("\n")

    # remove empty str item from list
    # remove current dir indicator(".") if it is output with find
    if out[0] == ".":
        out = out[1:-1]
    else:
        out = out[0:-1]

    lines = []
    for line in out:
        line = line.replace("./", "", 1)
        lines.append(line)

    return lines


# TODO: use fileinput methods to iterate over stdin?
def get_lines(**kwargs):
    """
    If stdin is from a pipe or file redirection, process input.
    Otherwise, spawn subprocess to get a file/dir listing.

    Return list of lines given some delimiter. (only NEWLINE supported for now)
    """

    mode = os.fstat(sys.stdin.fileno()).st_mode
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        print("PIPE or FILE REDIRECTION, processing input.")
        lines = sys.stdin.readlines()
    else:
        print("No PIPE or FILE REDIRECTION, walking cwd.")
        lines = get_files_and_dirs()

    return lines


def main():
    # parser = get_parser()
    # args = vars(parser.parse_args())
    # lines = get_lines()

    tui = Interface()
    tui.run()


if __name__ == "__main__":
    logging.basicConfig(filename="debug.log", level=logging.DEBUG)
    cProfile.run('main()')

