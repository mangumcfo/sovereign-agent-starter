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
    led.approve(ob["id"], approved_by="owner")        # clears the breath-gate
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    assert credit["type"] == "credit"


def test_gate_denial_blocks_and_is_recorded(tmp_path):
    led = ObligationLedger(root=tmp_path, gate=DENY)
    ob = led.open("Risky change", material=True)
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner")    # gate denies -> raises
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


def test_ungated_standalone_material_is_fail_closed(tmp_path):
    # AH-1 (Option A, the operator-ratified 2026-07-08): a gate-less ledger must NOT mean "no gate to satisfy" —
    # for a MATERIAL obligation it means "cannot approve here at all" (structurally barred from GREEN
    # auto-flow). It can neither close without approval NOR self-approve; approve() itself fail-closes.
    # (Superseded the pre-2026-07-08 posture where a gate-less material self-approve was auto-granted —
    # that encoded the very defect AH-1 names.) A non-material one is unaffected; and with no attestor
    # wired, no node receipt is minted (the Phase-1 receipt shape is preserved).
    led = ObligationLedger(root=tmp_path)
    ob = led.open("standalone-material", material=True)
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="~/proof.json")        # no approval → blocked
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner")        # gate-less + material → DENIED (fail-closed)
    assert led._is_approved(ob["id"]) is False              # the denial did not mint an approval
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="~/proof.json")        # still un-closeable — the bar is structural
    assert led.verify_chain() is True                       # the denial is recorded, chain intact

    nb = led.open("standalone-nonmaterial", material=False)
    led.approve(nb["id"], approved_by="owner")           # non-material keeps the permissive default
    credit = led.close(nb["id"], evidence="~/proof.json")  # non-material closes freely (unchanged)
    assert "node_receipt" not in credit["receipt"]
    assert led.verify_chain() is True


def test_external_gate_mode_does_not_auto_approve(tmp_path):
    """audit 2026-06-13d #16: gate_mode='external' returns a PENDING disposition — it must NOT flip the
    obligation to approved, and a material obligation must stay un-closeable (out-of-band human gate)."""
    from sovereign_agent.obligations.node_integration import wire_node_ledger

    class FakeNode:
        def _self_attest(self, event, details):
            return {"memory_root": "merkle_root_deadbeef", "event": event, "details": details}

    led = wire_node_ledger(root=tmp_path, node=FakeNode(), gate_mode="external", principal_id="owner")
    ob = led.open("external-gated material", material=True)
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner")          # external → not granted
    assert not any(e.get("type") == "approval" and e.get("approves") == ob["id"]
                   and e.get("disposition") == "approved" for e in led._entries())
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/x hash a1b2c3d4e5f60718")  # material + un-approved → blocked


def test_node_integration_smoke_real_compliance(tmp_path):
    """Wire the REAL ComplianceEngine via node_integration; a close must carry a node receipt."""
    from sovereign_agent.obligations.node_integration import wire_node_ledger

    class FakeNode:
        def _self_attest(self, event, details):
            return {"memory_root": "merkle_root_deadbeef", "event": event, "details": details}

    led = wire_node_ledger(root=tmp_path, node=FakeNode(), mode="sovereign")  # real gate (default)
    ob = led.open("Wire Phase 3 Node API /obligations", material=True)
    appr = led.approve(ob["id"], approved_by="owner")  # REAL disposition by the authenticated principal
    assert appr["approved_by"] == "owner"              # actor is the real principal, not a simulated stand-in
    assert appr["disposition"] == "approved"
    assert appr["gate"]["real"] is True and appr["gate"]["approver"] == "owner"
    credit = led.close(ob["id"], evidence="/repo/server.py hash a1b2c3d4e5f60718")
    # the close carries a real node attestation (Merkle root from the node)
    assert credit["receipt"]["node_receipt_hash"] == "merkle_root_deadbeef"
    assert led.verify_chain() is True


# ── AH-1 closure proofs (Option A, the operator-ratified 2026-07-08) ──────────────────────────────────────
# The sealed claim: material events are "structurally barred from any GREEN auto-flow"; the system is
# non-autonomous on material actions. Each test below FAILS against the pre-2026-07-08 code (which
# auto-granted gate-less material approvals and never enforced opener≠approver) and PASSES after.

def test_ah1_gateless_material_cannot_self_approve(tmp_path):
    """(a) A raw gate-less ledger — exactly what an autonomous agent/CLI holds — CANNOT mint an
    approval for a MATERIAL obligation. approve() fail-closes (records a denial, raises); the card
    stays un-approved and un-closeable. Pre-change: approve() auto-granted 'approved' and the card
    closed with no human gate (the AH-1 attack)."""
    led = ObligationLedger(root=tmp_path, principal_id="agent-nohuman")
    ob = led.open("promote to prod", material=True)          # same principal opens…
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="agent-nohuman")  # …and cannot approve itself (fail-closed)
    assert led._is_approved(ob["id"]) is False
    # the denial is on the record (evidence trail), loud not silent
    assert any(e.get("type") == "approval" and e.get("approves") == ob["id"]
               and e.get("disposition") == "denied" for e in led._entries())
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")  # structurally barred


def test_ah1_material_opener_equals_approver_is_not_approved(tmp_path):
    """(b) opener == approver on a MATERIAL obligation, recorded WITHOUT a real breath-gate (here a
    directly-appended self-approval, as a rubber-stamp or tampered chain would produce), does NOT
    count as approved and cannot close. Pre-change: is_approved() checked only disposition, so this
    self-approval read as approved and the material card closed."""
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    ob = led.open("wire money", material=True)               # owner defaults to principal_id
    # inject an 'approved' self-approval with NO real gate (opener == approver, gate absent)
    led._append({"type": "approval", "id": "ap_self", "approves": ob["id"],
                 "approved_by": "owner", "disposition": "approved", "gate": None,
                 "principal_id": "owner"})
    assert led._is_approved(ob["id"]) is False               # opener≠approver: self-approval barred
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")


def test_ah1_legitimate_gated_material_flow_still_works(tmp_path):
    """(c) The legitimate flow is UNBROKEN: distinct proposer (owner) and human approver, gate wired.
    A real breath-gate disposition (opener≠approver) approves and the material card closes end-to-end.
    Also covers the single-owner sovereign case: same principal opening+approving is honored ONLY
    through a real gate (gate.real) — see test_material_requires_approval / node_integration smoke."""
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)  # gate wired
    ob = led.open("promote ledger", owner="node", material=True)  # proposer = node
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")  # un-approved → blocked
    led.approve(ob["id"], approved_by="owner")             # distinct human approver clears the gate
    assert led._is_approved(ob["id"]) is True
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    assert credit["type"] == "credit"
    assert led.verify_chain() is True


def test_ah1_nonmaterial_permissive_default_unchanged(tmp_path):
    """(d) Non-material behavior is UNCHANGED — GREEN routine actions were never in scope of the bar.
    A gate-less non-material obligation may still be approved (permissive default) and closes; and a
    non-material obligation closes without any approval at all (existing GREEN auto-flow)."""
    led = ObligationLedger(root=tmp_path, principal_id="agent")
    ob = led.open("green tweak", material=False)
    led.approve(ob["id"], approved_by="agent")               # gate-less non-material approve: permitted
    assert led._is_approved(ob["id"]) is True                # opener==approver OK for non-material
    assert led.close(ob["id"], evidence="~/proof.json")["type"] == "credit"
    nb = led.open("another green tweak", material=False)
    assert led.close(nb["id"], evidence="~/proof.json")["type"] == "credit"  # no approval needed
    assert led.verify_chain() is True
