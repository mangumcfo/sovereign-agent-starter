"""R22-3 source-citation lineage — success-metric regression test.
Pins: a path-like source_ref resolves (file + passage) or close() raises (never false); additive +
forward-compatible (receipts without it unchanged)."""
import os, sys, tempfile, pytest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sovereign_agent.obligations.ledger import ObligationLedger

VAULT = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault"
REAL = ("kdp/series_02_building_the_agentic_harness/vol_01_sovereign_inference_and_memory/"
        'v1.0/manuscript_v1.6.md#"bl-verify"')

def _led(tmp):
    return ObligationLedger(root=str(tmp), principal_id="KM-1176")

@pytest.mark.skipif(not Path(VAULT).exists(), reason="books vault not present")
def test_resolving_source_ref_lands_on_receipt():
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner="KM-1176", material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by="KM-1176")
        led.close(o["id"], evidence="path", evidence_tier="E1",
                  source_ref=REAL, method="manual-cite", authorized_by_spec="GB_R22_Derivation_Specs")
        rec = next(e["receipt"] for e in led._entries() if e.get("type")=="credit")
        assert rec["source_ref"] == REAL and rec["method"] == "manual-cite"

def test_false_source_ref_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner="KM-1176", material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by="KM-1176")
        with pytest.raises(ValueError):
            led.close(o["id"], evidence="path", evidence_tier="E1",
                      source_ref="kdp/does/not/exist.md")

def test_forward_compatible_without_provenance():
    with tempfile.TemporaryDirectory() as d:
        led = _led(Path(d))
        o = led.open(title="x", owner="KM-1176", material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by="KM-1176")
        led.close(o["id"], evidence="path", evidence_tier="E1")
        rec = next(e["receipt"] for e in led._entries() if e.get("type")=="credit")
        assert "source_ref" not in rec
