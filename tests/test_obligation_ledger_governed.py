"""R-23 Phase 2 — governed obligation lifecycle (breath-gate + node receipts).

Core logic is tested with fake gate/attestor callables (decoupled). A smoke test wires the
REAL node ComplianceEngine via node_integration to prove the seam mints a node receipt.
"""
import pytest

from sovereign_agent.obligations import ObligationLedger


APPROVE = lambda action, ob: {"status": "approved", "req_id": "r1"}
DENY = lambda action, ob: {"status": "denied", "req_id": "r1", "reason": "not yet"}
ATTESTOR = lambda action_class, pid, payload, summary: {"receipt_hash": "node_rcpt_abc123def456"}


def test_material_obligation_requires_gate_approval(tmp_path):
    led = ObligationLedger(root=tmp_path, gate=APPROVE)
    ob = led.open("Promote ledger to default path", material=True)
    # close before approval is refused (human primacy)
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    led.approve(ob["id"], approved_by="km-1176")        # clears the breath-gate
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    assert credit["type"] == "credit"


def test_gate_denial_blocks_and_is_recorded(tmp_path):
    led = ObligationLedger(root=tmp_path, gate=DENY)
    ob = led.open("Risky change", material=True)
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="km-1176")    # gate denies -> raises
    # the denial is on the record, and the obligation cannot close
    assert any(e.get("type") == "approval" and e.get("disposition") == "denied"
               for e in led._entries())
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")


def test_non_material_closes_without_approval_even_when_gated(tmp_path):
    led = ObligationLedger(root=tmp_path, gate=APPROVE)
    ob = led.open("Minor GREEN tweak", material=False)
    credit = led.close(ob["id"], evidence="~/proof.json")  # no approval needed
    assert credit["type"] == "credit"


def test_close_mints_and_links_node_receipt(tmp_path):
    led = ObligationLedger(root=tmp_path, attestor=ATTESTOR)
    ob = led.open("Closed with node attestation")
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    assert credit["receipt"]["node_receipt_hash"] == "node_rcpt_abc123def456"
    assert credit["receipt"]["node_receipt"]["receipt_hash"] == "node_rcpt_abc123def456"


def test_ungated_standalone_unchanged(tmp_path):
    # Phase-1 behavior: no gate/attestor => material flag is not enforced, no node receipt
    led = ObligationLedger(root=tmp_path)
    ob = led.open("standalone", material=True)
    credit = led.close(ob["id"], evidence="~/proof.json")
    assert "node_receipt" not in credit["receipt"]
    assert led.verify_chain() is True


def test_node_integration_smoke_real_compliance(tmp_path):
    """Wire the REAL ComplianceEngine via node_integration; a close must carry a node receipt."""
    from sovereign_agent.obligations.node_integration import wire_node_ledger

    class FakeNode:
        def _self_attest(self, event, details):
            return {"memory_root": "merkle_root_deadbeef", "event": event, "details": details}

    led = wire_node_ledger(root=tmp_path, node=FakeNode(), mode="sovereign")  # real gate (default)
    ob = led.open("Wire Phase 3 Node API /obligations", material=True)
    appr = led.approve(ob["id"], approved_by="km-1176")  # REAL disposition by the authenticated principal
    assert appr["approved_by"] == "km-1176"              # actor is the real principal, not a simulated stand-in
    assert appr["disposition"] == "approved"
    assert appr["gate"]["real"] is True and appr["gate"]["approver"] == "km-1176"
    credit = led.close(ob["id"], evidence="/repo/server.py hash a1b2c3d4e5f60718")
    # the close carries a real node attestation (Merkle root from the node)
    assert credit["receipt"]["node_receipt_hash"] == "merkle_root_deadbeef"
    assert led.verify_chain() is True
