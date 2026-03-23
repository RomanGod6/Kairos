import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from keyboardVariants import keyboard_variants



def test_keyboard_variants():
    word = "vonahi"
    expected_variants = [
      "conahi", "fonahi", "gonahi",  "bonahi"
    ]
    variants = keyboard_variants(word)
    for expected in expected_variants:
        assert expected in variants
    assert "vonahi" not in variants
