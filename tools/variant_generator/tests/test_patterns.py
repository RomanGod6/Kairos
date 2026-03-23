import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from patterns import name_to_pattern


def test_patterns():
    assert name_to_pattern("Autotask PSA") == r"autotask\s+psa"
    assert name_to_pattern("VSA X") == r"vsa\s+x"