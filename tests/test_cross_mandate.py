"""Phase 2 · Slice 2.1 — automated cross-mandate blocking (the operator-ratified).

Spec-first from S2-V4 *Federated Sovereignty* Ch 2 (mandate separation): "Each mandate is its own
constitutional surface. The operator carries the mandates; the federation does not aggregate them.
Cross-mandate operations require cross-mandate ceremony." This generalizes AH-1's opener≠approver
hardening to the MANDATE boundary: an approval/action on a MATERIAL obligation scoped to mandate M is
valid only if the acting principal HOLDS M (or carries an explicit cross-mandate authorization).

The gate is ADDITIONAL to — and composed with, never weakening — AH-1. money_path irrelevant (no funds).

The designated FAIL-BEFORE / PASS-AFTER proof is test_cross_mandate_barred_projection_fail_before,
written purely with open()/_append()/_is_approved() so it runs identically against the pre-change code
(git checkout of projection.py): pre-change is_approved ignores mandate ⇒ reads APPROVED (the gap);
post-change ⇒ BARRED. See obligations/mandate_guard.py for the mandate-representation assumption.
"""
import pytest

from sovereign_agent.obligations import ObligationLedger

APPROVE = lambda action, ob: {"status": "approved", "real": True, "approver": ob.get("approved_by")}


# (a) same-mandate approval still works — continuity; don't break AH-1's legitimate flows.
def test_same_mandate_approval_still_works(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)  # real gate
    ob = led.open("corp forecast promote", owner="node", material=True, mandate="corporate")
    # distinct human approver (AH-1) who HOLDS the corporate mandate (Slice 2.1)
    led.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"])
    assert led._is_approved(ob["id"]) is True
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    assert credit["type"] == "credit"
    assert led.verify_chain() is True


# (b) cross-mandate act BARRED at the ledger (fail-closed, raises + recorded).
def test_cross_mandate_approval_barred_fail_closed(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)  # real gate ⇒ AH-1 satisfied
    ob = led.open("family trust review", owner="node", material=True, mandate="family_office")
    with pytest.raises(PermissionError):
        # acting principal holds only 'corporate' — a cross-mandate act on a family_office obligation
        led.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"])
    assert led._is_approved(ob["id"]) is False
    # denial recorded loudly (evidence trail), not silent
    assert any(e.get("type") == "approval" and e.get("approves") == ob["id"]
               and e.get("disposition") == "denied"
               and "cross-mandate" in (e.get("gate") or {}).get("reason", "")
               for e in led._entries())
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")  # material + un-approved → blocked


# (b') FAIL-BEFORE / PASS-AFTER — pure projection proof (git-checkout-stable: no new signatures).
# Pre-change projection.is_approved ignores `mandate` ⇒ this reads APPROVED (the security gap).
# Post-change ⇒ BARRED. This is the designated before/after test.
def test_cross_mandate_barred_projection_fail_before(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    # hand-append a scoped MATERIAL debit + a REAL-gated approval by a principal holding the WRONG mandate
    # (owner ≠ approver + gate.real ⇒ AH-1 is satisfied; only the mandate gate can bar this).
    led._append({"type": "debit", "id": "ob_xm", "title": "wire family funds",
                 "owner": "node", "material": True, "mandate": "family_office",
                 "draft": True, "approved": False, "principal_id": "owner"})
    led._append({"type": "approval", "id": "ap_xm", "approves": "ob_xm",
                 "approved_by": "owner-corp", "disposition": "approved",
                 "gate": {"real": True, "approver": "owner-corp"},
                 "held_mandates": ["corporate"], "principal_id": "owner"})
    # POST: barred (holds corporate, obligation scoped family_office). PRE: this asserted True (the gap).
    assert led._is_approved("ob_xm") is False
    with pytest.raises(PermissionError):
        led.close("ob_xm", evidence="/repo/x.py hash a1b2c3d4e5f60718")


# (c) explicit cross-mandate authorization (the book's Ch 2 ceremony output) → permitted.
def test_explicit_cross_mandate_authorization_permitted(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("cross-mandate handoff", owner="node", material=True, mandate="family_office")
    # principal holds corporate only, BUT carries an explicit, declared cross-mandate authorization for
    # family_office (stands in for the ratified 3-receipt witness ceremony, §221-227).
    led.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"],
                cross_mandate_auth={"authorized": True, "mandate": "family_office",
                                    "ceremony": "cross_mandate_witness"})
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")["type"] == "credit"


# (c') a MISMATCHED cross_mandate_auth (authorizes a different mandate) does NOT open the boundary.
def test_mismatched_cross_mandate_auth_still_barred(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("family trust move", owner="node", material=True, mandate="family_office")
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"],
                    cross_mandate_auth={"authorized": True, "mandate": "civic"})  # wrong mandate
    assert led._is_approved(ob["id"]) is False


# (d) AH-1 opener≠approver STILL enforced on a scoped obligation (composition, not regression).
def test_ah1_opener_equals_approver_still_barred_when_scoped(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    ob = led.open("scoped self-approve", material=True, mandate="corporate")  # owner defaults to principal
    # gate-less + material ⇒ AH-1 fail-closes at approve() even though the mandate is held.
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner", held_mandates=["corporate"])
    assert led._is_approved(ob["id"]) is False
    # and a hand-appended self-approval (opener==approver, no real gate) is still barred by AH-1,
    # regardless of a matching held mandate — the two gates compose.
    led._append({"type": "approval", "id": "ap_self", "approves": ob["id"],
                 "approved_by": "owner", "disposition": "approved", "gate": None,
                 "held_mandates": ["corporate"], "principal_id": "owner"})
    assert led._is_approved(ob["id"]) is False


# (e) single-owner sovereign flow still legal — the AH-1 real-gate exception; unscoped ⇒ mandate no-op.
def test_single_owner_sovereign_unscoped_still_legal(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner", gate=APPROVE)  # real gate
    ob = led.open("sovereign single-mandate action", material=True)  # NO mandate ⇒ unscoped
    led.approve(ob["id"], approved_by="owner")  # same principal opens+approves THROUGH a real gate
    assert led._is_approved(ob["id"]) is True     # AH-1 real-gate exception honored
    assert led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")["type"] == "credit"


# (f) non-material scoped obligation is UNAFFECTED (the bar is material-only, mirroring AH-1).
def test_nonmaterial_scoped_unaffected(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="agent")
    ob = led.open("green scoped tweak", material=False, mandate="family_office")
    # gate-less non-material approve by a principal holding a DIFFERENT mandate: still permitted (not gated).
    led.approve(ob["id"], approved_by="agent", held_mandates=["corporate"])
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence="~/proof.json")["type"] == "credit"
