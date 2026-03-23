import yaml 




def load_abbreviations(yaml_file):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    
    abbreviations = {}
    for product in data['products']:
        for abbr in product.get('abbreviations', []):
            abbr = abbr.lower()
            abbreviations[abbr] = product["canonical_name"]
        for slang_term in product.get('slang', []):
            slang_term = slang_term.lower()
            abbreviations[slang_term] = product["canonical_name"]    
    return abbreviations

def expand(token, abbrev_map):
    token = token.lower()
    return abbrev_map.get(token)