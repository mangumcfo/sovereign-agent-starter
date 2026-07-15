"""S2 close-out mini-slices (the operator go 2026-07-09) — the two named backlog items that finish S2's code column.

Slice A — CLASS-LEVEL QUORUM CONFIG (S2-V3 *The Harness That Builds Itself* Ch 5, manuscript_v1.6
L483: "The quorum is a Charter decision, not a technical default — the operator sets it per proposal
class"; the Ch 2 playbook's `cross_role_veto_quorum` mapping). Graduates the designed-toward remainder
named in cross_role_review_v0.1.yaml as_built_notes ("per-proposal-class quorum config surface").
RULE: ObligationLedger(class_quorum={classification: N}) sets a Charter FLOOR for MATERIAL obligations
of that class — resolved at open() and STAMPED on the debit (is_approved stays a pure replay); a
per-obligation declaration may raise the bar, never undercut the Charter floor. No config ⇒ unchanged.

Slice B — HELD-MANDATE RESOLUTION FROM NODE IDENTITY (S2-V4 *Federated Sovereignty* Ch 2 §215:
"the operator's identity key is shared across mandates... the constitutional surface at each mandate
is separate" — the operator CARRIES the mandates). Graduates the designed-toward remainder named in
cross_mandate_v0.1.yaml ("Held-mandate resolution from per-mandate node identity / role config").
RULE: ObligationLedger(node_identity={principal: [mandates]}) makes identity GOVERN a known
principal's held mandates at approve() — stamped with held_mandates_source="node_identity"; a
self-declaration claiming a mandate identity does not grant is DENIED + recorded, fail-closed.
Unknown principals / no registry keep the 2.1 action-site declaration flow, byte-identical.
"""
import pytest

from sovereign_agent.obligations import ObligationLedger
from sovereign_agent.obligations import quorum_guard, mandate_guard

APPROVE = lambda action, ob: {"status": "approved", "real": True, "approver": ob.get("approved_by")}
EV = "/repo/x.py hash a1b2c3d4e5f60718"


# ── Slice A · class-level quorum config ──────────────────────────────────────

# (a1) Charter class floor applies: material C2 under {"C2": 2} needs TWO distinct reviewers.
def test_class_floor_requires_two(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           class_quorum={"C2": 2})
    ob = led.open("charter-classed material act", owner="node", material=True)  # no per-ob quorum
    assert ob["quorum"] == 2 and ob["quorum_source"] == "class:C2"  # floor stamped at open()
    led.approve(ob["id"], approved_by="owner-corp")
    assert led._is_approved(ob["id"]) is False                      # 1 of 2 ⇒ pending
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence=EV)
    led.approve(ob["id"], approved_by="owner-audit")
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence=EV)["type"] == "credit"
    assert led.verify_chain() is True


# (a2) A declaration cannot UNDERCUT the Charter floor (declared 1 < floor 2 ⇒ effective 2).
def test_declaration_cannot_undercut_floor(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           class_quorum={"C2": 2})
    ob = led.open("attempted quorum undercut", owner="node", material=True, quorum=1)
    assert ob["quorum"] == 2 and ob["quorum_source"] == "class:C2"
    led.approve(ob["id"], approved_by="owner-corp")
    assert led._is_approved(ob["id"]) is False                      # the floor held


# (a3) A declaration MAY raise the bar above the floor (declared 3 > floor 2 ⇒ effective 3).
def test_declaration_may_raise_above_floor(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           class_quorum={"C2": 2})
    ob = led.open("extra-review act", owner="node", material=True, quorum=3)
    assert ob["quorum"] == 3 and "quorum_source" not in ob          # the declaration set the bar
    led.approve(ob["id"], approved_by="a")
    led.approve(ob["id"], approved_by="b")
    assert led._is_approved(ob["id"]) is False                      # 2 of 3 ⇒ pending
    led.approve(ob["id"], approved_by="c")
    assert led._is_approved(ob["id"]) is True


# (a4) Non-material keeps quorum-1 regardless of class config (same boundary as AH-1/2.1/2.2).
def test_class_floor_material_only(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           class_quorum={"C2": 3})
    ob = led.open("routine non-material", owner="node")            # material=False
    assert "quorum" not in ob
    led.approve(ob["id"], approved_by="anyone")
    assert led._is_approved(ob["id"]) is True


# (a5) No config / unknown class ⇒ byte-identical prior behavior (no quorum field stamped).
def test_no_config_unchanged(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE)
    ob = led.open("plain material", owner="node", material=True)
    assert "quorum" not in ob and "quorum_source" not in ob
    led2 = ObligationLedger(root=tmp_path / "b", principal_id="node", gate=APPROVE,
                            class_quorum={"C9": 4})                 # different class than C2 default
    ob2 = led2.open("material, class not in config", owner="node", material=True)
    assert "quorum" not in ob2


# (a6) Malformed config values fail closed to floor 1 (never 0/negative; garbage never crashes open()).
def test_malformed_class_config_fails_closed():
    assert quorum_guard.class_quorum_floor({"C2": "garbage"}, "C2") == 1
    assert quorum_guard.class_quorum_floor({"C2": -3}, "C2") == 1
    assert quorum_guard.class_quorum_floor({"C2": 0}, "C2") == 1
    assert quorum_guard.class_quorum_floor(None, "C2") == 1
    assert quorum_guard.class_quorum_floor({"C2": 2}, None) == 1
    assert quorum_guard.effective_quorum("garbage", 2) == 2
    assert quorum_guard.effective_quorum(None, 1) == 1


# ── Slice B · held-mandate resolution from node identity ────────────────────

# (b1) Identity RESOLVES a known principal's mandates — no declaration needed at the action site.
def test_identity_resolves_held_mandates(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           node_identity={"owner-corp": ["corporate", "fiduciary"]})
    ob = led.open("corporate-scoped act", owner="node", material=True, mandate="corporate")
    entry = led.approve(ob["id"], approved_by="owner-corp")            # nothing declared — identity governs
    assert entry["held_mandates"] == ["corporate", "fiduciary"]
    assert entry["held_mandates_source"] == "node_identity"
    assert led._is_approved(ob["id"]) is True


# (b2) FAIL-CLOSED: identity-resolved principal NOT holding the obligation's mandate is barred (2.1 path).
def test_identity_lacking_mandate_barred(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           node_identity={"owner-family": ["family-office"]})
    ob = led.open("corporate-scoped act", owner="node", material=True, mandate="corporate")
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner-family")              # identity holds family-office only
    assert led._is_approved(ob["id"]) is False


# (b3) FAIL-CLOSED: a self-declaration claiming a mandate identity does not grant is DENIED + recorded.
def test_overclaim_denied_and_recorded(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           node_identity={"owner-family": ["family-office"]})
    ob = led.open("corporate-scoped act", owner="node", material=True, mandate="corporate")
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner-family",
                    held_mandates=["corporate"])                    # forged claim — identity refuses it
    denials = [e for e in led.iter_entries()
               if e.get("type") == "approval" and e.get("disposition") == "denied"]
    assert len(denials) == 1 and "overclaim" in denials[0]["gate"]["reason"]
    assert denials[0]["held_mandates"] == ["family-office"]         # the chain records what identity holds
    assert led._is_approved(ob["id"]) is False
    assert led.verify_chain() is True


# (b4) Declared-subset-of-identity is fine — identity's list is what gets stamped (identity governs).
def test_declared_subset_stamps_identity_list(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           node_identity={"owner-corp": ["corporate", "civic"]})
    ob = led.open("civic-scoped act", owner="node", material=True, mandate="civic")
    entry = led.approve(ob["id"], approved_by="owner-corp", held_mandates=["civic"])
    assert entry["held_mandates"] == ["corporate", "civic"]         # registry list, not the declaration
    assert entry["held_mandates_source"] == "node_identity"
    assert led._is_approved(ob["id"]) is True


# (b5) Unknown principal / no registry ⇒ the 2.1 declared flow, byte-identical (backward-compatible).
def test_unknown_principal_keeps_declared_flow(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           node_identity={"someone-else": ["corporate"]})
    ob = led.open("corporate-scoped act", owner="node", material=True, mandate="corporate")
    entry = led.approve(ob["id"], approved_by="owner-new", held_mandates=["corporate"])
    assert entry["held_mandates"] == ["corporate"]
    assert "held_mandates_source" not in entry                      # declared, not identity-resolved
    assert led._is_approved(ob["id"]) is True


# (b6) Pure-helper contract (no ledger): resolution + overclaim surface exactly per the docstring.
def test_resolve_helper_contract():
    assert mandate_guard.resolve_held_mandates(None, "p", ["a"]) == (["a"], "declared", [])
    assert mandate_guard.resolve_held_mandates({"q": ["a"]}, "p", None) == ([], "declared", [])
    held, src, over = mandate_guard.resolve_held_mandates({"p": ["a", "b"]}, "p", ["a", "c"])
    assert held == ["a", "b"] and src == "node_identity" and over == ["c"]
    held, src, over = mandate_guard.resolve_held_mandates({"p": "not-a-list"}, "p", ["a"])
    assert held == [] and src == "node_identity" and over == ["a"]  # malformed registry ⇒ holds nothing


# ── Composition: both slices together on one chain ──────────────────────────

# (c1) Class floor + identity resolution compose: 2 distinct identity-resolved mandate-holders approve.
def test_slices_compose(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=APPROVE,
                           class_quorum={"C2": 2},
                           node_identity={"owner-corp": ["corporate"], "owner-audit": ["corporate"],
                                          "owner-family": ["family-office"]})
    ob = led.open("cross-reviewed corporate act", owner="node", material=True, mandate="corporate")
    assert ob["quorum"] == 2
    led.approve(ob["id"], approved_by="owner-corp")
    assert led._is_approved(ob["id"]) is False                      # quorum pending
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="owner-family")              # wrong mandate — barred, not counted
    assert led._is_approved(ob["id"]) is False
    led.approve(ob["id"], approved_by="owner-audit")                   # second distinct valid reviewer
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence=EV)["type"] == "credit"
    assert led.verify_chain() is True
