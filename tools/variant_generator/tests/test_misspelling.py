import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from misspelling import double_reduction_variants, transposition_variants



def test_double_reduction_variants():
    word = "letter"
    expected_variants = [
        "leter", 
    ]
    variants = double_reduction_variants(word)
    for expected in expected_variants:
        assert expected in variants
    assert "letter" not in variants

def test_transposition_variants():
    word = "form"
    expected_variants = [
        "from", "ofrm"
    ]
    variants = transposition_variants(word)
    for expected in expected_variants:
        assert expected in variants
    assert "form" not in variants