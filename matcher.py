from util import initialize_matrix


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


    # fuzzy_match makes two assumptions
    # 1. "pattern" is given in lowercase if "case_sensitive" is false
    # 2. "pattern" is already normalized if "normalize" is true
    def fuzzymatch_v1(self, chars, pattern, case=True, normalize=True, with_pos=True):
        score_matrix, max_score, match_positions = self.get_score(chars, pattern)
        if with_pos:
            return max_score, match_positions
        else:
            return max_score


    def compute_scores(self, pattern, lines, sort=True):
        processed = []
        lines = lines.split("\n")
        for line in lines:
            line = line.rstrip("\n")
            score, match_positions = self.fuzzymatch_v1(line, pattern)
            processed.append((line, score, match_positions))

        if sort:
            # sort lines in ascending order by score and line length
            return sorted(processed, key=lambda x: (x[1], len(x[0])), reverse=False)

        return processed


if __name__ == "__main__":
    import sys
    import os

    matcher = Matcher()
    scored_lines = matcher.compute_scores(sys.argv[1], sys.argv[2])
    for line, score, match_positions in scored_lines:
        print("LINE: {0}; SCORE: {1}; MATCHES: {2};".format(line, str(score), match_positions))

