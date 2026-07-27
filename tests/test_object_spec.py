"""S5-05-E8-3: the object model is specified as a named, versioned spec."""
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "docs/specs/S5-05_sovereign_object_model_v0.1.md"


def test_spec_present_named_and_covers_all_modules():
    assert SPEC.exists(), "the named, versioned spec must be present"
    text = SPEC.read_text()
    assert "Spec v0.1" in text  # versioned
    for mod in ("identity.py", "registry.py", "lifecycle.py", "manifest.py",
                "proofs.py", "scope.py", "migrate.py", "inheritance.py"):
        assert mod in text, f"spec must cover objects/{mod}"
    for eid in ("E1-2", "E2-1", "E2-2", "E3-1", "E3-3", "E4-1", "E4-4", "E5-1",
                "E5-2", "E5-4", "E6-1", "E6-4", "E7-1", "E7-3", "E8-1", "E8-3", "E8-4"):
        assert eid in text, f"spec must map ledger id {eid}"
