import pytest


@pytest.fixture(scope="module")
def data():
    return [
        # pattern, low score, high score
        ("ff", "fuzzyfinder", "fuzzy-finder"),
        ("ff", "fuzzy-blurry-finder", "fuzzyfinder"),
        ("br", "foob-r", "fo-bar"),
        ("foob", "foo-bar", "foobar"),
        ("oob", "foobar", "out-of-bound"),
    ]