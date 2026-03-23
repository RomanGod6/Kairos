import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from expander import load_abbreviations, expand

YAML_PATH = "../../../config/products.yaml"


def test_load_abbreviations():
    abbrev_map = load_abbreviations(YAML_PATH)
    assert abbrev_map.get("atask") == "Autotask PSA"
    assert abbrev_map.get("autotask") == "Autotask PSA"
    assert abbrev_map.get("at") is None

def test_expand_known():
    abbrev_map = load_abbreviations(YAML_PATH)
    assert expand("vsa", abbrev_map) == "VSA X"
    assert expand("siris", abbrev_map) == "Datto BCDR"

def test_expand_unknown():
    abbrev_map = load_abbreviations(YAML_PATH)
    assert expand("xyz", abbrev_map) is None