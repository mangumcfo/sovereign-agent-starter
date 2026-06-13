"""R22-1 Evidence-Packet Exports — success-metric regression test.
Pins: a built packet self-verifies on a clean machine (no ledger), is deterministic, tamper is rejected."""
import os, sys, json, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import export_packet as EP
from sovereign_agent.obligations.ledger import ObligationLedger

def _fixture_ledger(tmp):
    led = ObligationLedger(root=str(tmp), principal_id="KM-1176")
    ids = []
    for i in range(3):
        o = led.open(title=f"fixture {i}", owner="KM-1176", material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by="KM-1176")
        led.close(o["id"], evidence=f"artifact path {i}", evidence_tier="E1")
        ids.append(o["id"])
    return led, ids

def test_packet_self_verifies_and_is_deterministic_and_tamper_evident():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _, ids = _fixture_ledger(root)
        b1 = EP.build_packet(ids, root)
        b2 = EP.build_packet(ids, root)
        # determinism (ignore the human note line)
        assert {k: b1[k] for k in ("entries","receipts","merkle_proof","sha")} == \
               {k: b2[k] for k in ("entries","receipts","merkle_proof","sha")}
        # success metric: self-verifies with ONLY the bundle (clean machine)
        ok, why = EP.verify_packet(b1)
        assert ok, why
        assert b1["manifest"]["receipt_count"] == 3
        # tamper → rejected
        b1["receipts"][0]["evidence"] = "TAMPERED"
        bad, _ = EP.verify_packet(b1)
        assert not bad
