def transposition_variants(word: str) -> list[str]:
    variants = []
    word = word.lower()
    for i, char in enumerate(word[:-1]):
        if word[i] != word[i+1]:
            if word[i] != word[i+1] and word[i] != ' ' and word[i+1] != ' ':
                transposed_word = word[:i] + word[i+1] + char + word[i+2:]
                variants.append(transposed_word)

    return variants


def double_reduction_variants(word: str) -> list [str]:
    variants = []
    word = word.lower()
    for i in range(len(word) - 1):
        if word[i] == word[i + 1]:
            reduced_word = word[:i] + word[i + 1:]
            variants.append(reduced_word)

    return variants