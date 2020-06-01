#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import cProfile

from tui import Selector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--algo", action="store_true", default="v1", help="Algorithm to use for matching.")
    parser.add_argument("-s", "--show", action="store_true", default=True, help="Indicate characters that have a match.")
    parser.add_argument("-i", "--ignore-case", action="store_true", default=False, help="Perform case-insensitive matching.")
    parser.add_argument("infile", nargs="?", type=argparse.FileType("r"), default=sys.stdin, help="Input file.")

    args = parser.parse_args()

    Selector(
        algo=args.algo,
        case_sensitive=args.ignore_case,
        show_matches=args.show,
        infile=args.infile,
    ).run()


if __name__ == "__main__":
    logging.basicConfig(filename="debug.log", level=logging.DEBUG)
    cProfile.run("main()")
