"""R22-5 Tiered qualified-reviewer gates — success-metric regression test.
Pins: class_y rejected for under-qualified reviewer, accepted for qualified; policy is YAML data."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import qualification_gate as QG

def test_class_y_tiers_by_qualification_from_yaml():
    pol = QG.load_policy()
    assert QG.required_qualification("class_y", pol) == "owner"   # policy is data, not code
    # success metric
    assert QG.check("controller", "class_y", pol)[0] is False     # under-qualified → rejected
    assert QG.check("owner", "class_y", pol)[0] is True           # qualified → accepted
    assert QG.check("controller", "class_x", pol)[0] is True      # controller fits class_x
    assert QG.check("viewer", "class_x", pol)[0] is False         # viewer under-qualified
    # unknown class default-denies (loud)
    assert QG.check("owner", "no_such_class", pol)[0] is False
