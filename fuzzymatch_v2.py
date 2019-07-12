from enum import Enum


SCORE_MATCH = 16
SCORE_GAP_START = -3
SCORE_GAP_EXTENSION = -1
BONUS_BOUNDARY = SCORE_MATCH / 2
BONUS_NON_ALNUM = SCORE_MATCH / 2
BONUS_CAMEL_123 = BONUS_BOUNDARY + SCORE_GAP_EXTENSION
BONUS_CONSECUTIVE = -(SCORE_GAP_START + SCORE_GAP_EXTENSION)
BONUS_FIRST_CHAR_MULTIPLIER = 2


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


# NormalizeRunes implementation (normalizes latin script letters)
def normalize(chars):
    pass


def traceback(score_matrix, start_pos, chars, pattern):
    END, DIAG, UP, LEFT = range(4)
    aligned_chars = []
    aligned_pattern = []
    c_idx, p_idx = start_pos
    move = next_move(score_matrix, c_idx, p_idx)
    match_positions = []
    while (move != END):
        if move == DIAG:
            match_positions.append(c_idx)
            aligned_chars.append(chars[c_idx - 1])
            aligned_pattern.append(pattern[p_idx - 1])
            c_idx -= 1
            p_idx -= 1
        elif move == UP:
            aligned_chars.append(chars[c_idx - 1])
            aligned_pattern.append('$')
            c_idx -= 1
        else:
            match_positions.append(c_idx)
            aligned_chars.append('$')
            aligned_pattern.append(pattern[p_idx - 1])
            p_idx -= 1
        move = next_move(score_matrix, c_idx, p_idx)

    aligned_chars.append(chars[c_idx - 1])
    aligned_pattern.append(pattern[p_idx - 1])

    print("Match positions:", match_positions)
    return ''.join(reversed(aligned_chars)), ''.join(reversed(aligned_pattern))


def next_move(score_matrix, c_idx, p_idx):
    diag = score_matrix[c_idx - 1][p_idx - 1]
    up = score_matrix[c_idx - 1][p_idx]
    left = score_matrix[c_idx][p_idx - 1]

    if diag >= up:
        return 1 if diag != 0 else 0 # 1 signals a DIAG move. 0 signals the end
    elif up > diag:
        return 2 if up != 0 else 0 # UP move or end
    elif left > diag and left > up:
        return 3 if left != 0 else 0
    else:
        return 0


def fuzzymatch_v2(chars, pattern, backtrack=True):
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
    max_score_pos = (0, 0)
    match_positions = []
    for c_idx in range(0, c_length):
        for p_idx in range(0, p_length):
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

    if backtrack:
        alignment1, alignment2 = traceback(score_matrix, max_score_pos, chars, pattern)
        print(alignment1)
        print(alignment2)

    return score_matrix, max_score, match_positions
