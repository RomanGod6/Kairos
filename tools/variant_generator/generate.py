import sys
from expander import load_abbreviations, expand
from keyboardVariants import keyboard_variants
from misspelling import double_reduction_variants, transposition_variants
from patterns import name_to_pattern
from phonetic import phonetic_variants

YAML_PATH = "../../config/products.yaml"


def generate_variants(product_name: str, abbrev_map: dict) -> dict:
    name = product_name.lower()

    return {
        "keyboard": keyboard_variants(name),
        "phonetic": phonetic_variants(name),
        "double_reduction": double_reduction_variants(name),
        "transposition": transposition_variants(name),
        "pattern": name_to_pattern(name),
        "expanded": expand(name, abbrev_map),
    }


if __name__ == "__main__":
    abbrev_map = load_abbreviations(YAML_PATH)

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        import yaml
        import json
        with open(YAML_PATH) as f:
            data = yaml.safe_load(f)
        
        results = {}
        for product in data['products']:
            name = product['canonical_name']
            name = name.lower()
            variants = generate_variants(name, abbrev_map)

            results[name] = variants

        with open("../../data/training/synthetic/variants.json", "w") as f:
            json.dump(results, f, indent=2)

    else:
        product_name = sys.argv[1]
        result = generate_variants(product_name, abbrev_map)
        for key, value in result.items():
            print(f"{key}: {value}")