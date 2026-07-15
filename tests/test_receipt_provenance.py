"""R22-3 source-citation lineage — success-metric regression test.
Pins: a path-like source_ref resolves (file + passage) or close() raises (never false); additive +
forward-compatible (receipts without it unchanged). Self-contained: builds a tmp books vault and
points BREATHLINE_BOOKS_VAULT at it (no host-specific vault required)."""
import os, sys, tempfile, pytest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sovereign_agent.obligations.ledger import ObligationLedger

REF_PATH = "series_x/vol_01/v1.0/manuscript_v1.0.md"
REAL = REF_PATH + '#"bl-verify"'
OWNER = "owner"


def _led(tmp):
    return ObligationLedger(root=str(tmp), principal_id=OWNER)


@pytest.fixture()
def books_vault(monkeypatch, tmp_path):
    """A minimal vault: <vault>/kdp/<REF_PATH> containing the cited passage."""
    kdp = tmp_path / "vault" / "kdp"
    doc = kdp / REF_PATH
    doc.parent.mkdir(parents=True)
    doc.write_text("… the bl-verify passage lives here …", encoding="utf-8")
    monkeypatch.setenv("BREATHLINE_BOOKS_VAULT", str(kdp))
    return kdp


def test_resolving_source_ref_lands_on_receipt(books_vault):
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner=OWNER, material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by=OWNER)
        led.close(o["id"], evidence="path", evidence_tier="E1",
                  source_ref=REAL, method="manual-cite", authorized_by_spec="R22_Derivation_Specs")
        rec = next(e["receipt"] for e in led._entries() if e.get("type") == "credit")
        assert rec["source_ref"] == REAL and rec["method"] == "manual-cite"


def test_false_source_ref_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner=OWNER, material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by=OWNER)
        with pytest.raises(ValueError):
            led.close(o["id"], evidence="path", evidence_tier="E1",
                      source_ref="kdp/does/not/exist.md")


def test_forward_compatible_without_provenance():
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner=OWNER, material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by=OWNER)
        led.close(o["id"], evidence="path", evidence_tier="E1")
        rec = next(e["receipt"] for e in led._entries() if e.get("type") == "credit")
        assert "source_ref" not in rec
