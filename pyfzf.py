#!/usr/bin/env python

"""
Python implementation of fzf.
"""

import os
import sys
import stat
import argparse

from enum import Enum

from util import print_matrix, initialize_matrix, get_files_and_dirs


SCORE_MATCH = 16
SCORE_GAP_START = -3
SCORE_GAP_EXTENSION = -1
BONUS_BOUNDARY = SCORE_MATCH / 2
BONUS_NON_ALNUM = SCORE_MATCH / 2
BONUS_CAMEL_123 = BONUS_BOUNDARY + SCORE_GAP_EXTENSION
BONUS_CONSECUTIVE = -(SCORE_GAP_START + SCORE_GAP_EXTENSION)
BONUS_FIRST_CHAR_MULTIPLIER = 2

# scoreMatch*3+bonusBoundary*bonusFirstCharMultiplier+
# bonusBoundary*2+2*scoreGapStart+4*scoreGapExtention)


class CharType(Enum):
    LOWER = 1
    UPPER = 2
    NUMBER = 3
    NON_ALNUM = 4


# charClassOf implementation
def get_char_type(char):
    if char.isalnum():
        if char.islower():
            return CharType.LOWER
        elif char.isupper():
            return CharType.UPPER
        else:
            return CharType.NUMBER
    else:
        return CharType.NON_ALNUM


# bonusFor implementation
def calc_bonus(prev, curr):
    if prev is CharType.NON_ALNUM and curr is not CharType.NON_ALNUM:
        return BONUS_BOUNDARY
    elif prev is CharType.LOWER and curr is CharType.UPPER:
        return BONUS_CAMEL_123
    elif prev is not CharType.NUMBER and curr is CharType.NUMBER:
        return BONUS_CAMEL_123
    elif curr is CharType.NON_ALNUM:
        return BONUS_NON_ALNUM
    else:
        return 0


def normalize(chars):
    """Normalize latin script letters."""

    pass


def calc_score(chars, pattern, backtrack=True):
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
    prev_char_type = CharType.NON_ALNUM

    score = 0
    max_score = 0
    max_score_pos = (0, 0)
    match_positions = []
    for c_idx in range(0, c_length):
        if consecutive > 0:
            p_idx += 1
        if p_idx < p_length:
            c = chars[c_idx]
            curr_char_type = get_char_type(c)
            if c == pattern[p_idx]:
                score += SCORE_MATCH
                bonus = calc_bonus(prev_char_type, curr_char_type)
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
    if not p_idx >= (p_length - 1):
        return score_matrix, 0, None
    elif backtrack:
        return backtrace(chars, pattern, max_score_pos)
    else:
        return score_matrix, max_score, match_positions


def backtrace(chars, pattern, start_pos):
    c_length = len(chars)
    p_length = len(pattern)

    # +1 for gap row and gap column
    rows = c_length + 1
    cols = p_length + 1
    score_matrix = initialize_matrix(rows, cols)

    in_gap = False
    consecutive = 0
    first_bonus = 0
    prev_char_type = CharType.NON_ALNUM

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
            curr_char_type = get_char_type(c)
            if c == pattern[p_idx]:
                score += SCORE_MATCH
                bonus = calc_bonus(prev_char_type, curr_char_type)
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
def fuzzymatch_v1(chars, pattern, case=True, normalize=True, with_pos=True):
    score_matrix, max_score, match_positions = calc_score(chars, pattern)
    if with_pos:
        return max_score, match_positions
    else:
        return max_score


def main(input_strings):
    for chars, pattern in input_strings:
        print("Chars:", chars)
        print("Pattern:", pattern)

        score_matrix, max_score, match_positions = calc_score(chars, pattern, backtrack=False)
        print("Max Score:", max_score)
        print("Match Positions: ", match_positions)
        print("Score Matrix:\n")
        print_matrix(score_matrix)
        print()

        score_matrix, max_score, match_positions = calc_score(chars, pattern, backtrack=True)
        print("Max Score:", max_score)
        print("Match Positions: ", match_positions)
        print("Score Matrix:\n")
        print_matrix(score_matrix)
        print()

        # score_matrix, max_score, match_positions = fuzzymatch_v2(chars, pattern, backtrack=True)
        # print("Max Score:", max_score)
        # print("Match Positions: ", match_positions)
        # print("Score Matrix:\n")
        # print_matrix(score_matrix)
        # print()



# TODO: replace with generator/yield
def process_lines(lines, pattern, algo):
    for index, line in enumerate(lines):
        line = line.rstrip("\n")
        score, match_positions = algo(line, pattern)
        print(index, line, score, match_positions)


def get_parser():
    parser = argparse.ArgumentParser(description="Command-line fuzzy finder")
    parser.add_argument("-p", help="the pattern to match input against")
    parser.add_argument("-f", help="file to use as input for fuzzy matching")
    parser.add_argument("--algo", help="algorithm to use for fuzzy matching")

    return parser


def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())

    if args["p"]:
        pattern = args["p"]
    else:
        sys.exit()

    algo = fuzzymatch_v1
    if args["algo"] == "v2":
        print("Implementation pending. Using fuzzymatch_v1.")
    else:
        print("No algorithm selected. Defaulting to fuzzymatch_v1.")

    if args["f"]:
        input_file = args["f"]
        if os.path.isfile(input_file):
            with open(input_file, "r") as f:
                lines = f.readlines()
                process_lines(lines, pattern, algo)
        else:
            print("File does not exist.")
    else:
        mode = os.fstat(sys.stdin.fileno()).st_mode

        # If stdin is from a pipe or file redirection, process input.
        # Otherwise, walk current dir and use file/dir listing as input.
        if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
            print("PIPE or FILE REDIRECTION, processing input.")
            lines = sys.stdin.readlines()
            process_lines(lines, pattern, algo)
        else:
            print("No PIPE or FILE REDIRECTION, walking cwd.")
            lines = get_files_and_dirs()
            process_lines(lines, pattern, algo)


if __name__ == '__main__':
    command_line_runner()

