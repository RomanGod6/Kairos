
def name_to_pattern(name: str) -> str:
    split = name.lower().split()
    pattern = r"\s+".join(split)
    return pattern