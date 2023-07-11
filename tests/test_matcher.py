from pyfzf.matcher import FuzzyMatch


fuzzy_match = FuzzyMatch()


def test_fuzzy_match_special_char_bonus():
    low_score = fuzzy_match.process("fuzzyfinder", "ff")
    high_score = fuzzy_match.process("fuzzy-finder", "ff")

    assert high_score > low_score


def test_fuzzy_match_gap_penalty():
    low_score = fuzzy_match.process("fuzzy-blurry-finder", "ff")
    high_score = fuzzy_match.process("fuzzyfinder", "ff")

    assert high_score > low_score


def test_fuzzy_match_first_char_bonus():
    low_score = fuzzy_match.process("foob-r", "br")
    high_score = fuzzy_match.process("fo-bar", "br")

    assert high_score > low_score


def test_fuzzy_match_first_char_chunk():
    low_score = fuzzy_match.process("foobar", "oob")
    high_score = fuzzy_match.process("out-of-bound", "oob")

    assert high_score > low_score


def test_fuzzy_match_consecutive_bonus():
    low_score = fuzzy_match.process("foo-bar", "foob")
    high_score = fuzzy_match.process("foobar", "foob")

    assert high_score > low_score
