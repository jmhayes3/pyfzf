import itertools
import numpy as np


SCORE_MATCH = 16
SCORE_GAP_START = -3
SCORE_GAP_EXTENSION = -1
BONUS_BOUNDARY = SCORE_MATCH // 2
BONUS_NON_ALNUM = SCORE_MATCH // 2
BONUS_CAMEL_123 = BONUS_BOUNDARY + SCORE_GAP_EXTENSION
BONUS_CONSECUTIVE = -(SCORE_GAP_START + SCORE_GAP_EXTENSION)
BONUS_FIRST_CHAR_MULTIPLIER = 2


def calc_bonus(prev, curr):
    if prev is None:
        if not curr.isalnum():
            return BONUS_NON_ALNUM
    elif not prev.isalnum() and curr.isalnum():
        return BONUS_BOUNDARY
    elif not prev.isalnum() and curr.isnumeric():
        return BONUS_CAMEL_123
    elif prev.islower() and curr.isupper():
        return BONUS_CAMEL_123
    return 0


class FuzzyMatch:

    def __init__(self, pattern=[], text=[]) -> None:
        self.pattern = pattern
        self.text = text
        self.matrix = np.zeros((len(text) + 1, len(pattern) + 1), int)


    def process(self, text, pattern):
        matrix = np.zeros((len(text) + 1, len(pattern) + 1), int)
        rows = matrix.shape[0]
        cols = matrix.shape[1]

        in_gap = False
        consecutive = 0

        for i, j in itertools.product(range(1, rows), range(1, cols)):
        # for i in range(rows):
        #     for j in range(cols):
            score = 0

            if text[i - 1] == pattern[j - 1]:
                score += SCORE_MATCH

                if i > 1:
                    bonus = calc_bonus(text[i - 2], text[i - 1])
                else:
                    bonus = calc_bonus(None, text[i - 1])

                if bonus == BONUS_BOUNDARY:
                    consecutive = 1
                elif consecutive > 1:
                    bonus += consecutive

                if text[i - 1] == pattern[0]:
                    bonus *= BONUS_FIRST_CHAR_MULTIPLIER

                score += bonus
                in_gap = False
                consecutive += 1
            else:
                if in_gap:
                    score = SCORE_GAP_EXTENSION
                else:
                    score = SCORE_GAP_START

                in_gap = True
                consecutive = 0

            match = matrix[i - 1, j - 1] + score
            delete = matrix[i - 1, j] + score
            insert = matrix[i, j - 1] + score

            matrix[i, j] = max(match, delete, insert)

        max_score = matrix.max()
        match_indices = []

        for _ in range(cols - 1):
            matrix_flip = np.flip(np.flip(matrix, 0), 1)
            row, col = np.unravel_index(matrix_flip.argmax(), matrix_flip.shape)
            row_, col_ = np.subtract(matrix.shape, (row + 1, col + 1))

            if matrix[row_, col_] == 0:
                break

            match_indices.append(row_ - 1)
            matrix = matrix[0:row_, 0:col_]

        return max_score, match_indices
