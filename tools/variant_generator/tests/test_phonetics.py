import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from phonetic import phonetic_variants, sounds_like



def test_phonetic_variants():
    word = "datto"
    expected_variants = [
        "dato", "daddo"
    ]
    variants = phonetic_variants(word)
    for expected in expected_variants:
        assert expected in variants
    assert "datto" not in variants  

def test_sounds_like():
    assert sounds_like("datto", "dato")
    assert sounds_like("datto", "daddo")
    assert not sounds_like("datto", "backup")