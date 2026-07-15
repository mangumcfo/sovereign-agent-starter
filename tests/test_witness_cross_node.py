"""S2 closure wave — W1 (3-receipt witness ceremony) + W2 (cross-node review).

Spec-first: cross_mandate_witness_v0.1.yaml (staged pre-wave, the operator go 2026-07-08) from S2-V4 Ch 2
§221-227; W2 composes W1 (transport) + slice 2.2 (quorum counting) from sealed sources only.

Designated FAIL-BEFORE / PASS-AFTER: test_witness_backed_auth_fail_before — pre-wave
projection.is_approved accepted ANY declared cross_mandate_auth dict carrying a witness_ref without
checking the chain (the gap: a fabricated witness_ref minted authority); post-wave it validates the
witness structurally and bars the fabrication. Pure _append()/_is_approved(), git-checkout-stable.
"""
import pytest

from sovereign_agent.obligations import ObligationLedger
from sovereign_agent.obligations import witness as W
from sovereign_agent.obligations.cross_node import import_remote_approval

APPROVE = lambda action, ob: {"status": "approved", "real": True, "approver": ob.get("approved_by")}


def _two_nodes(tmp_path):
    a = ObligationLedger(root=tmp_path / "node_a", principal_id="node-a", gate=APPROVE)
    b = ObligationLedger(root=tmp_path / "node_b", principal_id="node-b", gate=APPROVE)
    return a, b


# ── W1 — the ceremony ─────────────────────────────────────────────────────────
def test_three_receipts_land_on_both_chains(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("family trust transfer review", owner="node", material=True, mandate="family_office")
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="owner-corp")
    r = W.receive(b, o)
    rec = W.witness_seal(a, b, o, r)
    assert rec["seal_status"] == "SEALED_HOST_PENDING"          # honest sentinel, never a fake seal
    assert W.validate_witness_ref(a._entries(), rec) is True    # sealed at chain A
    assert W.validate_witness_ref(b._entries(), rec) is True    # sealed at chain B
    assert a.verify_chain() is True and b.verify_chain() is True


def test_witness_refuses_unanchored_receive(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("x", owner="node", material=True, mandate="family_office")
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="owner-corp")
    r = W.receive(b, o)
    forged = dict(r, originating_hash="deadbeef")
    with pytest.raises(ValueError):
        W.witness_seal(a, b, o, forged)                          # mismatched anchor — fail-closed


def test_witness_backed_approval_clears_gate(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("cross-mandate act", owner="node", material=True, mandate="family_office")
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="owner-corp")
    rec = W.witness_seal(a, b, o, W.receive(b, o))
    # approver holds only 'corporate' — authority comes from the WITNESSED ceremony, replay-verifiable
    a.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"],
              cross_mandate_auth={"authorized": True, "mandate": "family_office", "witness_ref": rec})
    assert a._is_approved(ob["id"]) is True


# (fail-before/pass-after) — a FABRICATED witness_ref must not mint authority.
def test_witness_backed_auth_fail_before(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="owner")
    led._append({"type": "debit", "id": "ob_w", "title": "forged ceremony attempt",
                 "owner": "node", "material": True, "mandate": "family_office",
                 "draft": True, "approved": False, "principal_id": "owner"})
    led._append({"type": "approval", "id": "ap_w", "approves": "ob_w",
                 "approved_by": "owner-corp", "disposition": "approved",
                 "gate": {"real": True}, "held_mandates": ["corporate"],
                 "cross_mandate_auth": {"authorized": True, "mandate": "family_office",
                                        "witness_ref": {"witness_id": "fabricated",
                                                        "originating_hash": "x", "receiving_hash": "y"}},
                 "principal_id": "owner"})
    # POST: barred (no xm_witness entry on-chain matches). PRE: read APPROVED (the gap).
    assert led._is_approved("ob_w") is False


def test_bare_declared_auth_still_accepted_21_floor(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("legacy declared auth", owner="node", material=True, mandate="family_office")
    led.approve(ob["id"], approved_by="owner-corp", held_mandates=["corporate"],
                cross_mandate_auth={"authorized": True, "mandate": "family_office"})  # no witness_ref
    assert led._is_approved(ob["id"]) is True                    # 2.1 floor unchanged


# ── W2 — cross-node review ────────────────────────────────────────────────────
def test_cross_node_quorum_two_nodes(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("charter amendment", owner="node", material=True, quorum=2, mandate="family_office")
    # local reviewer 1 (holds the mandate)
    a.approve(ob["id"], approved_by="owner-audit", held_mandates=["family_office"])
    assert a._is_approved(ob["id"]) is False                     # 1 of 2 — pending
    # remote reviewer on node B approves; ceremony runs; approval imported to A
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="owner-trustee")
    rec = W.witness_seal(a, b, o, W.receive(b, o))
    remote = b._append({"type": "approval", "id": "rap_1", "approves": ob["id"],
                        "approved_by": "owner-trustee", "disposition": "approved",
                        "gate": {"real": True, "approver": "owner-trustee"},
                        "held_mandates": ["family_office"], "principal_id": "node-b"})
    imp = import_remote_approval(a, remote, rec)
    assert imp["imported"] is True and imp["remote_assurance"] == "UNVERIFIED"  # honest sentinel
    assert a._is_approved(ob["id"]) is True                      # quorum met across two nodes
    assert a.verify_chain() is True


def test_import_refuses_tampered_remote_entry(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("tamper case", owner="node", material=True, quorum=2, mandate="family_office")
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="owner-trustee")
    rec = W.witness_seal(a, b, o, W.receive(b, o))
    remote = b._append({"type": "approval", "id": "rap_t", "approves": ob["id"],
                        "approved_by": "owner-trustee", "disposition": "approved",
                        "gate": {"real": True}, "held_mandates": ["family_office"],
                        "principal_id": "node-b"})
    tampered = dict(remote, approved_by="mallory")               # hash no longer re-derives
    before = len(a._entries())
    with pytest.raises(ValueError):
        import_remote_approval(a, tampered, rec)
    assert len(a._entries()) == before                           # refused import leaves NO residue


def test_import_refuses_without_local_witness(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("no ceremony ran", owner="node", material=True, quorum=2, mandate="family_office")
    remote = b._append({"type": "approval", "id": "rap_n", "approves": ob["id"],
                        "approved_by": "owner-trustee", "disposition": "approved",
                        "gate": {"real": True}, "held_mandates": ["family_office"],
                        "principal_id": "node-b"})
    with pytest.raises(ValueError):
        import_remote_approval(a, remote, {"witness_id": "never-sealed",
                                           "originating_hash": "x", "receiving_hash": "y"})


def test_imported_approval_gets_no_privileged_path(tmp_path):
    a, b = _two_nodes(tmp_path)
    ob = a.open("owner smuggle attempt", owner="node", material=True, quorum=2, mandate="family_office")
    o = W.originate(a, ob["id"], target_mandate="family_office", initiated_by="node")
    rec = W.witness_seal(a, b, o, W.receive(b, o))
    # the OPENER's own approval arriving via import still never counts toward a multi-party quorum
    remote = b._append({"type": "approval", "id": "rap_o", "approves": ob["id"],
                        "approved_by": "node", "disposition": "approved",
                        "gate": {"real": True}, "held_mandates": ["family_office"],
                        "principal_id": "node-b"})
    import_remote_approval(a, remote, rec)
    assert a._is_approved(ob["id"]) is False                     # opener excluded (2.2), imported or not
