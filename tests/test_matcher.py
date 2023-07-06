from pyfzf.matcher import FuzzyMatch


# pattern, low score, high score
inputs = [
    ("ff", "fuzzyfinder", "fuzzy-finder"),
    ("ff", "fuzzy-blurry-finder", "fuzzyfinder"),
    ("br", "foob-r", "fo-bar"),
    ("foob", "foo-bar", "foobar"),
    ("oob", "foobar", "out-of-bound"),
]


def test_fuzzy_match_special_char_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("fuzzyfinder", "ff")
    high_score = fuzzy_match.process("fuzzy-finder", "ff")

    assert high_score > low_score


def test_fuzzy_match_gap_penalty():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("fuzzy-blurry-finder", "ff")
    high_score = fuzzy_match.process("fuzzyfinder", "ff")

    assert high_score > low_score


def test_fuzzy_match_first_char_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foob-r", "br")
    high_score = fuzzy_match.process("fo-bar", "br")

    assert high_score > low_score


def test_fuzzy_match_consecutive_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foo-bar", "foob")
    high_score = fuzzy_match.process("foobar", "foob")

    assert high_score > low_score


def test_fuzzy_match_first_char_chunk():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foobar", "oob")
    high_score = fuzzy_match.process("out-of-bound", "oob")

    assert high_score > low_score


def test_fuzzy_match_v1_special_char_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("fuzzyfinder", "ff")
    high_score = fuzzy_match.process("fuzzy-finder", "ff")

    assert high_score > low_score


def test_fuzzy_match_gap_penalty():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("fuzzy-blurry-finder", "ff")
    high_score = fuzzy_match.process("fuzzyfinder", "ff")

    assert high_score > low_score


def test_fuzzy_match_first_char_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foob-r", "br")
    high_score = fuzzy_match.process("fo-bar", "br")

    assert high_score > low_score


def test_fuzzy_match_consecutive_bonus():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foo-bar", "foob")
    high_score = fuzzy_match.process("foobar", "foob")

    assert high_score > low_score


def test_fuzzy_match_first_char_chunk():
    fuzzy_match = FuzzyMatch(with_pos=False)
    low_score = fuzzy_match.process("foobar", "oob")
    high_score = fuzzy_match.process("out-of-bound", "oob")

    assert high_score > low_score
