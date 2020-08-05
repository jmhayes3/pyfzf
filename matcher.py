import itertools
import numpy as np

from functools import lru_cache

SCORE_MATCH = 16
SCORE_GAP_START = -3
SCORE_GAP_EXTENSION = -1
BONUS_BOUNDARY = SCORE_MATCH // 2
BONUS_NON_ALNUM = SCORE_MATCH // 2
BONUS_CAMEL_123 = BONUS_BOUNDARY + SCORE_GAP_EXTENSION
BONUS_CONSECUTIVE = -(SCORE_GAP_START + SCORE_GAP_EXTENSION)
BONUS_FIRST_CHAR_MULTIPLIER = 2

LOWER = 1
UPPER = 2
NUMBER = 3
NON_ALNUM = 4


@lru_cache(maxsize=128)
def get_char_type(char):
    if char.isalnum():
        if char.islower():
            return LOWER
        elif char.isupper():
            return UPPER
        else:
            return NUMBER
    else:
        return NON_ALNUM


@lru_cache(maxsize=128)
def calc_bonus(prev, curr):
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


# if backtrack is False, don't traverse backwards to find shorter match
def get_score(chars, pattern, backtrack=True):
    c_length = len(chars)
    p_length = len(pattern)

    # +1 for gap row and gap column
    rows = c_length + 1
    cols = p_length + 1

    # initialize matrix
    score_matrix = [[0 for col in range(cols)] for row in range(rows)]

    p_idx = 0
    in_gap = False
    consecutive = 0
    first_bonus = 0
    prev_char_type = NON_ALNUM

    score = 0
    max_score = 0
    max_score_pos = (0, 0)
    match_positions = []
    for c_idx in range(c_length):
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
                if c == pattern[0] and c_idx == 0:
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
        return traceback(chars, pattern, max_score_pos)
    else:
        return score_matrix, max_score, match_positions


def traceback(chars, pattern, start_pos):
    c_length = len(chars)
    p_length = len(pattern)

    # +1 for gap row and gap column
    rows = c_length + 1
    cols = p_length + 1
    score_matrix = [[0 for col in range(cols)] for row in range(rows)]

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
                if c == pattern[0] and c_idx == 0:
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


def fuzzymatch_v1(chars, pattern, case=True, with_pos=True, debug=False):
    if not case:
        pattern = pattern.lower()
    score_matrix, max_score, match_positions = get_score(chars, pattern)
    if debug:
        return score_matrix, max_score, match_positions
    elif with_pos:
        return max_score, match_positions
    else:
        return max_score


class SmithWaterson:

    def __init__(self):
        pass

    def matrix(self, a, b, match_score=3, gap_cost=2):
        H = np.zeros((len(a) + 1, len(b) + 1), np.int)

        for i, j in itertools.product(range(1, H.shape[0]), range(1, H.shape[1])):
            match = H[i - 1, j - 1] + (match_score if a[i - 1] == b[j - 1] else - match_score)
            delete = H[i - 1, j] - gap_cost
            insert = H[i, j - 1] - gap_cost
            H[i, j] = max(match, delete, insert, 0)

        return H

    def traceback(self, H, b, b_='', old_i=0):
        # flip H to get index of **last** occurrence of H.max() with np.argmax()
        H_flip = np.flip(np.flip(H, 0), 1)
        i_, j_ = np.unravel_index(H_flip.argmax(), H_flip.shape)
        i, j = np.subtract(H.shape, (i_ + 1, j_ + 1))  # (i, j) are **last** indexes of H.max()
        if H[i, j] == 0:
            return b_, j
        b_ = b[j - 1] + '-' + b_ if old_i - i > 1 else b[j - 1] + b_
        return self.traceback(H[0:i, 0:j], b, b_, i)

    def search(self, chars, pattern, match_score=3, gap_cost=2):
        chars, pattern = chars.upper(), pattern.upper()
        H = self.matrix(chars, pattern, match_score, gap_cost)
        pattern_, pos = self.traceback(H, pattern)
        return chars[pos:pos + len(pattern_)]


class FuzzyMatchV1:

    def __init__(self):
        pass

    def search(self, chars, pattern):
        pass


class FuzzyMatchV2:

    def __init__(self):
        pass

    def search(self, chars, pattern):
        pass


class ExactNaiveMatch:

    def __init__(self):
        pass

    def search(self, chars, pattern):
        pass


sw = SmithWaterson()
print(sw.search("ggttgacta", "tgttacgg"))
