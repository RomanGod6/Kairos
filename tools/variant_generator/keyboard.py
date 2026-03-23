ADJACENCY_MAP = {
"a" : ["q", "w", "s", "z"],
"b" : ["v", "g", "h", "n"],
"c" : ["x", "d", "f", "v"],
"d" : ["s", "e", "r", "f", "c", "x"],
"e" : ["w", "s", "d", "r"],
"f" : ["d", "r", "t", "g", "v", "c"],
"g" : ["f", "t", "y", "h", "b", "v"],
"h" : ["g", "y", "u", "j", "n", "b"],
"i" : ["u", "j", "k", "o"],
"j" : ["h", "u", "i", "k", "m", "n"],
"k" : ["j", "i", "o", "l", "m"],
"l" : ["k", "o", "p"],
"m" : ["n", "j", "k"],
"n" : ["b", "h", "j", "m"],
"o" : ["i", "k", "l", "p"],
"p" : ["o", "l"],
"q" : ["a", "w", "s"],
"r" : ["e", "d", "f", "t"],
"s" : ["a", "w", "e", "d", "x", "z"],
"t" : ["r", "f", "g", "y"],
"u" : ["y", "h", "j", "i"],
"v" : ["c", "f", "g", "b"],
"w" : ["q", "a", "s", "e"],
"x" : ["z", "s", "d", "c"],
"y" : ["t", "g", "h", "u"],
"z" : ["a", "s", "x"],
}



def keyboard_variants(word: str) -> list[str]:
    variants = []
    word = word.lower()
    for i, char in enumerate(word):
        if char in ADJACENCY_MAP:
            for adjacent_char in ADJACENCY_MAP[char]:
                variant = word[:i] + adjacent_char + word[i+1:]
                variants.append(variant)

    return variants