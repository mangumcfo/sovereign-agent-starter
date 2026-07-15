"""Phase 2 · Slice 2.2 — multi-role quorum enforcement (the operator go after gate-green checkpoint).

Spec-first from S2-V3 *The Harness That Builds Itself* Ch 5 ("The Veto Quorum and the Failure Modes
It Closes"): "A quorum above one closes the single-compromised-reviewer failure mode: a drifting
reviewer cannot wave a proposal through alone." The book's Ch 5 receipt names this exact build:
"the multi-role quorum + federation-portable cross_role_review_v0.1.yaml (planned)."

RULE: a MATERIAL obligation declaring quorum N (open(quorum=N)) is approved only when N DISTINCT
principals have each recorded a gate-valid approval — each individually passing AH-1 and the 2.1
mandate guard; the OPENER never counts toward a multi-party quorum. Composed with, never weakening,
AH-1 + 2.1. No quorum field ⇒ quorum 1 ⇒ pre-slice behavior, byte-identical.

The designated FAIL-BEFORE / PASS-AFTER proof is test_quorum_pending_projection_fail_before, written
purely with _append()/_is_approved() so it runs identically against the pre-change code (git checkout
of projection.py): pre-change is_approved ignores `quorum` ⇒ 1-of-2 reads APPROVED (the gap);
post-change ⇒ PENDING. See obligations/quorum_guard.py for scope + veto-interplay notes.
"""
import pytest

from sovereign_agent.obligations import ObligationLedger

APPROVE = lambda action, ob: {"status": "approved", "real": True, "approver": ob.get("approved_by")}


# (a) default quorum-1 flow byte-identical — continuity (no quorum field ⇒ single approval suffices).
def test_default_quorum_one_unchanged(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("routine material promote", owner="node", material=True)
    led.approve(ob["id"], approved_by="owner")
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")["type"] == "credit"
    assert led.verify_chain() is True


# (b) quorum 2: ONE reviewer in ⇒ PENDING (not approved, close barred); TWO distinct ⇒ approved.
def test_quorum_two_needs_two_distinct_reviewers(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("charter boundary shift", owner="node", material=True, quorum=2)
    led.approve(ob["id"], approved_by="owner-corp")          # reviewer 1 — recorded, but quorum pending
    assert led._is_approved(ob["id"]) is False
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")  # material + pending → blocked
    led.approve(ob["id"], approved_by="owner-audit")         # reviewer 2, distinct ⇒ quorum met
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")["type"] == "credit"


# (b') FAIL-BEFORE / PASS-AFTER — pure projection proof (git-checkout-stable: no new signatures).
# Pre-change projection.is_approved ignores `quorum` ⇒ 1-of-2 reads APPROVED (the gap). Post ⇒ PENDING.
def test_quorum_pending_projection_fail_before(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    led._append({"type": "debit", "id": "ob_q", "title": "amend family charter",
                 "owner": "node", "material": True, "quorum": 2,
                 "draft": True, "approved": False, "principal_id": "owner"})
    led._append({"type": "approval", "id": "ap_q1", "approves": "ob_q",
                 "approved_by": "owner-corp", "disposition": "approved",
                 "gate": {"real": True, "approver": "owner-corp"}, "principal_id": "owner"})
    # POST: pending (1 of 2). PRE: this asserted True (the gap).
    assert led._is_approved("ob_q") is False
    with pytest.raises(PermissionError):
        led.close("ob_q", evidence="/repo/x.py hash a1b2c3d4e5f60718")


# (c) DISTINCTNESS: the same reviewer approving twice is ONE voice, not quorum.
def test_same_reviewer_twice_is_not_quorum(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    led._append({"type": "debit", "id": "ob_d", "title": "dup-voice attempt",
                 "owner": "node", "material": True, "quorum": 2,
                 "draft": True, "approved": False, "principal_id": "owner"})
    for ap_id in ("ap_d1", "ap_d2"):
        led._append({"type": "approval", "id": ap_id, "approves": "ob_d",
                     "approved_by": "owner-corp", "disposition": "approved",
                     "gate": {"real": True, "approver": "owner-corp"}, "principal_id": "owner"})
    assert led._is_approved("ob_d") is False  # one distinct approver ≠ quorum 2


# (d) OPENER EXCLUDED from a multi-party quorum — even through a real gate. Declaring quorum > 1 is
# the operator's opt-in to multi-party review; the AH-1 single-owner exception governs quorum-1 only.
def test_opener_never_counts_toward_multi_party_quorum(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("self + one is not two reviewers", owner="node", material=True, quorum=2)
    led.approve(ob["id"], approved_by="node")            # opener, real gate — does NOT count
    led.approve(ob["id"], approved_by="owner-corp")          # one true reviewer
    assert led._is_approved(ob["id"]) is False            # still pending: opener excluded
    led.approve(ob["id"], approved_by="owner-audit")         # second true reviewer ⇒ met
    assert led._is_approved(ob["id"]) is True


# (e) COMPOSITION with AH-1 + 2.1: invalid approvals never count toward quorum.
def test_invalid_approvals_do_not_count_toward_quorum(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    led._append({"type": "debit", "id": "ob_c", "title": "scoped quorum action",
                 "owner": "node", "material": True, "quorum": 2, "mandate": "family_office",
                 "draft": True, "approved": False, "principal_id": "owner"})
    # AH-1-barred voice: opener self-approval, no real gate.
    led._append({"type": "approval", "id": "ap_c1", "approves": "ob_c",
                 "approved_by": "node", "disposition": "approved", "gate": None,
                 "held_mandates": ["family_office"], "principal_id": "owner"})
    # 2.1-barred voice: real gate but holds the WRONG mandate.
    led._append({"type": "approval", "id": "ap_c2", "approves": "ob_c",
                 "approved_by": "owner-corp", "disposition": "approved",
                 "gate": {"real": True}, "held_mandates": ["corporate"], "principal_id": "owner"})
    assert led._is_approved("ob_c") is False              # zero valid voices
    # two gate-valid, mandate-holding, distinct reviewers ⇒ met.
    for ap_id, who in (("ap_c3", "owner-audit"), ("ap_c4", "owner-trustee")):
        led._append({"type": "approval", "id": ap_id, "approves": "ob_c",
                     "approved_by": who, "disposition": "approved",
                     "gate": {"real": True}, "held_mandates": ["family_office"],
                     "principal_id": "owner"})
    assert led._is_approved("ob_c") is True


# (f) DISPLAY mirrors ENFORCEMENT: a quorum-pending obligation never displays approved
# (replay + full_log — the display-vs-enforce class).
def test_display_surfaces_never_overstate_quorum_pending(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("display honesty check", owner="node", material=True, quorum=2)
    led.approve(ob["id"], approved_by="owner-corp")          # 1 of 2 — pending
    rep = led.replay()
    rec = next(o for o in rep["all"] if o["id"] == ob["id"])
    assert rec.get("approved") is not True                # replay must not display approved
    log_rec = next(d for d in led.full_log() if d["id"] == ob["id"])
    assert log_rec.get("approved") is not True            # full_log must not display approved
    assert log_rec.get("status") != "approved"


# (g) NON-MATERIAL declaring quorum is UNAFFECTED (material-only scope, mirroring AH-1 + 2.1).
def test_nonmaterial_quorum_unaffected(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="agent")
    ob = led.open("green tweak with stray quorum", material=False, quorum=3)
    led.approve(ob["id"], approved_by="agent")
    assert led._is_approved(ob["id"]) is True             # non-material: quorum not in scope
    assert led.close(ob["id"], evidence="~/proof.json")["type"] == "credit"


# (h) MALFORMED quorum values fail closed to 1, never to 0 (a zero quorum would auto-approve).
def test_malformed_quorum_fails_closed_to_one(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    led._append({"type": "debit", "id": "ob_m", "title": "malformed quorum",
                 "owner": "node", "material": True, "quorum": "not-a-number",
                 "draft": True, "approved": False, "principal_id": "owner"})
    assert led._is_approved("ob_m") is False              # no approvals yet: quorum 1 still needs one
    led._append({"type": "approval", "id": "ap_m1", "approves": "ob_m",
                 "approved_by": "owner-corp", "disposition": "approved",
                 "gate": {"real": True}, "principal_id": "owner"})
    assert led._is_approved("ob_m") is True               # reads as quorum 1, one valid reviewer suffices
