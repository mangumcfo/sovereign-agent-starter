"""Federation Node Governance (s5_26 / reading Vol 28) — proof that a federation is governed node-to-node with no
central hub and no second authority center: the receiver validates a shared packet independently, a crossing is
gated by a peer-declared rule, and two nodes reconcile independently-computed roots — composing the sealed Sovereign
Object Model, building no federation registry of its own.

Pure composition (the object model is hashlib-based, no crypto substrate) — runs green on a bare public clone."""
import pytest

from sovereign_agent import federation as fed
from sovereign_agent.federation import ScopeRefusal
from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule

SRC = "federation-node:concord"  # symbolic source citation — accepted as-is by the object model


def _registry(tmp_path):
    reg = ObjectRegistry(str(tmp_path / "node"))
    reg.append("customer:C1", {"name": "Alpha"}, author="node-a", source_ref=SRC, at="2026-08-05", mandate="node-A")
    reg.append("customer:C2", {"name": "Beta"}, author="node-b", source_ref=SRC, at="2026-08-05", mandate="node-B")
    return reg


# --- cross-node validation: the receiver validates INDEPENDENTLY (no hub) ----------------------------------------

def test_share_node_state_produces_a_self_verifying_packet(tmp_path):
    reg = _registry(tmp_path)
    packet = fed.share_node_state(reg, at="2026-08-05")
    out = fed.validate_received(packet)
    assert out["accepted"] is True and out["failures"] == []
    assert out["root"] == packet["manifest"]["root"]


def test_validate_received_is_pure_offline_needs_only_the_packet(tmp_path):
    # the anti-hub core: validation is a pure function of the packet bytes — no registry, no network passed in
    reg = _registry(tmp_path)
    packet = fed.share_node_state(reg, at="2026-08-05")
    plain = dict(packet)  # a bare dict as a peer would receive over the wire
    assert fed.validate_received(plain)["accepted"] is True


def test_validate_received_rejects_a_tampered_packet(tmp_path):
    reg = _registry(tmp_path)
    packet = fed.share_node_state(reg, at="2026-08-05")
    # a peer alters an object's payload after the packet was built — the manifest root no longer recomputes
    packet["objects"][0]["payload"]["name"] = "TAMPERED"
    out = fed.validate_received(packet)
    assert out["accepted"] is False and out["failures"]


# --- scoped sharing: a crossing needs a peer-declared rule (no central grant authority) ---------------------------

def test_authorize_crossing_own_mandate_access_is_whole(tmp_path):
    reg = _registry(tmp_path)
    assert fed.authorize_crossing(reg, [], principal_mandate="node-A", obj_id="customer:C1", want="write") is True


def test_authorize_crossing_cross_node_needs_a_declared_rule(tmp_path):
    reg = _registry(tmp_path)
    rules = [SharingRule("customer:C1", to_mandate="node-B", scope="read")]
    # node-B may read C1 because node-A declared the rule
    assert fed.authorize_crossing(reg, rules, principal_mandate="node-B", obj_id="customer:C1", want="read") is True
    # ...but a read grant is not a write grant
    with pytest.raises(ScopeRefusal):
        fed.authorize_crossing(reg, rules, principal_mandate="node-B", obj_id="customer:C1", want="write")


def test_authorize_crossing_without_a_rule_is_refused(tmp_path):
    reg = _registry(tmp_path)
    with pytest.raises(ScopeRefusal):
        fed.authorize_crossing(reg, [], principal_mandate="node-B", obj_id="customer:C1", want="read")


# --- reconciliation: independently-computed roots, no central truth ----------------------------------------------

def test_node_root_and_reconcile_roots_agree_for_the_same_state(tmp_path):
    reg = _registry(tmp_path)
    r = fed.node_root(reg, "node-A")
    out = fed.reconcile_roots(r, r)
    assert out["aligned"] is True and out["divergence"] is None


def test_reconcile_roots_flags_divergence_without_overwriting(tmp_path):
    reg = _registry(tmp_path)
    ra = fed.node_root(reg, "node-A")
    rb = fed.node_root(reg, "node-B")  # a different mandate's objects -> a different root
    out = fed.reconcile_roots(ra, rb)
    assert out["aligned"] is False and out["divergence"] and out["node_root"] == ra and out["peer_root"] == rb
