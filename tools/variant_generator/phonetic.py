import jellyfish


PHONETIC_RULES = [
    ("tt", "t"),       # datto → dato
    ("ph", "f"),       # graphus → grafus
    ("ck", "k"),       # backup → bakup
    ("ea", "e"),       # kaseya → kasea (intermediate)
    ("ey", "ay"),      # kaseya → kasaya
    ("ey", "ee"),      # kaseya → kaseea
    ("s", "z"),        # kaseya → kazaya, saas → zaas
    ("z", "s"),        # reverse: vulscan → vulskan
    ("c", "k"),        # commerce → kommerce
    ("k", "c"),        # reverse: kaseya → caseya
    ("t", "d"),        # datto → daddo (soft t sounds like d)
    ("ou", "oo"),      # — future coverage
    ("ia", "ea"),      # — future coverage
    ("er", "ur"),      # — future coverage
]


def phonetic_variants(word: str) -> list[str]:
    variants = set()
    word = word.lower()
    for pattern, replacement in PHONETIC_RULES:
        if pattern in word:
            variant = word.replace(pattern, replacement)
            variants.add(variant)
    return list(variants)

def sounds_like(word1: str, word2: str) -> bool:
    word1 = word1.lower()
    word2 = word2.lower()
    return jellyfish.metaphone(word1) == jellyfish.metaphone(word2)
