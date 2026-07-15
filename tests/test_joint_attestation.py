"""R22-4 Cross-role veto / joint attestation — success-metric regression test.
Pins: 2-role action can't execute on 1; unresolved veto = default-deny; replay reconstructs the
veto in correct order (last veto/clear per role governs — mirrors the order-aware reopen/_is_closed fix)."""
import os, sys, tempfile, pytest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sovereign_agent.obligations.ledger import ObligationLedger

def _open(led, roles):
    o = led.open(title="material action", owner="owner", material=False,
                 requires_attestation=roles, veto_window="24h", next_gate="joint")
    led.approve(o["id"], approved_by="owner")
    return o["id"]

def test_cannot_execute_on_one_of_two_roles():
    with tempfile.TemporaryDirectory() as d:
        led = ObligationLedger(root=str(d), principal_id="node")
        oid = _open(led, ["cfo", "compliance"])
        led.attest(oid, "cfo", "alice")
        with pytest.raises(PermissionError):           # only 1 of 2 attested
            led.close(oid, evidence="path", evidence_tier="E1")
        led.attest(oid, "compliance", "bob")           # now both
        rec = led.close(oid, evidence="path", evidence_tier="E1")
        assert rec["type"] == "credit"

def test_unresolved_veto_default_denies():
    with tempfile.TemporaryDirectory() as d:
        led = ObligationLedger(root=str(d), principal_id="node")
        oid = _open(led, ["cfo"])
        led.attest(oid, "cfo", "alice")
        led.veto(oid, "compliance", reason="undisclosed liability")
        st = led.attestation_status(oid)
        assert st["vetoed"] and not st["can_execute"]
        with pytest.raises(PermissionError):
            led.close(oid, evidence="path", evidence_tier="E1")

def test_replay_reconstructs_veto_in_correct_order():
    with tempfile.TemporaryDirectory() as d:
        led = ObligationLedger(root=str(d), principal_id="node")
        oid = _open(led, ["cfo"]); led.attest(oid, "cfo", "alice")
        led.veto(oid, "compliance", reason="r1")       # veto
        assert led.attestation_status(oid)["vetoed"] is True
        led.clear_veto(oid, "compliance")              # clear → stands down
        assert led.attestation_status(oid)["vetoed"] is False
        led.veto(oid, "compliance", reason="r2")       # veto again → last event wins
        assert led.attestation_status(oid)["vetoed"] is True
        # after final clear, executes
        led.clear_veto(oid, "compliance")
        assert led.attestation_status(oid)["can_execute"] is True
        assert led.close(oid, evidence="path", evidence_tier="E1")["type"] == "credit"
