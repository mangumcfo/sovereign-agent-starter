# -*- coding: utf-8 -*-
"""Acceptance tests for Federation UX (S8 Vol 6) — federated_view.

Proves the federation surface renders cross-node state and owns no cross-node authority: it renders
each node's SUPPLIED snapshot read-only through the Sovereign Lens (V01), never fetches or commands a
node, never mutates one (each node stays sovereign), exposes NO write/act path (no central console),
and is mandate-scoped over both fields and nodes. Composes the Lens only. Crypto-free.
"""
import dataclasses
import pytest

from sovereign_agent.sovereign_ux.federated_view import federated_view, verify_federated, FederatedView
from sovereign_agent.sovereign_ux.lens import View, LensDrift


_STATES = {
    "node-a": {"posture": "aligned", "secret": "a-only", "balance": 10},
    "node-b": {"posture": "degraded", "secret": "b-only", "balance": 20},
}


# ---- renders cross-node state, read-only ------------------------------------------------------

def test_renders_each_node_through_the_lens_readonly():
    fed = federated_view(_STATES)
    assert set(fed.node_ids) == {"node-a", "node-b"}
    assert fed.node("node-a").content["posture"] == "aligned"
    assert fed.node("node-b").content["balance"] == 20
    assert isinstance(fed.node("node-a"), View)  # each node is a Sovereign Lens View


def test_rendering_does_not_mutate_a_node_state():
    state = {"posture": "aligned", "inner": {"k": 1}}
    fed = federated_view({"node-a": state})
    fed.node("node-a").content["inner"]["k"] = 999  # mutate the rendered view
    assert state == {"posture": "aligned", "inner": {"k": 1}}  # the node's source state is untouched


# ---- owns no cross-node authority · no central console ----------------------------------------

def test_federated_view_is_frozen():
    fed = federated_view(_STATES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        fed.views = {}  # type: ignore[misc] — a composition, not a mutable console


def test_no_write_or_act_method_on_the_federation_surface():
    public = {m for m in dir(FederatedView) if not m.startswith("_")}
    forbidden = {"write", "save", "commit", "apply", "mutate", "set", "update",
                 "run", "optimize", "execute", "command", "send", "act", "push"}
    assert not (public & forbidden), f"federation surface exposes a forbidden authority method: {public & forbidden}"


def test_renders_only_supplied_snapshots_imports_no_transport_or_messaging():
    # owns no cross-node authority: it renders state the caller SUPPLIES; it cannot fetch or command a
    # node — so it imports no messaging / transport / port client, only the Lens.
    from sovereign_agent.sovereign_ux import federated_view as fv
    import_lines = [ln for ln in open(fv.__file__).read().splitlines()
                    if ln.strip().startswith(("from ", "import ")) and "__future__" not in ln]
    # scan the module tokens only — strip the 'from'/'import' keywords so 'import' can't false-match 'port'
    joined = " ".join(import_lines)
    tokens = joined.replace("from", " ").replace("import", " ")
    assert ".lens" in joined                                   # composes the Sovereign Lens
    for banned in ("messaging", "collaboration", "resonance", "port", "transport", "socket", "requests", "http"):
        assert banned not in tokens, f"federation surface must not import a cross-node client: {banned}"


# ---- each node sovereign · mandate-scoped over fields AND nodes -------------------------------

def test_mandate_scopes_which_fields_each_node_exposes():
    scope = {"auditor": ["posture", "balance"]}  # the auditor mandate never sees 'secret'
    fed = federated_view(_STATES, mandate="auditor", scope=scope)
    for nid in fed.node_ids:
        assert "secret" not in fed.node(nid).content
        assert "posture" in fed.node(nid).content


def test_unmapped_mandate_is_admitted_nothing_deny_by_default():
    fed = federated_view(_STATES, mandate="stranger", scope={"auditor": ["posture"]})
    assert fed.node("node-a").content == {}  # deny-by-default: an un-mapped mandate sees no fields


def test_admits_scopes_which_nodes_are_visible():
    fed = federated_view(_STATES, admits=lambda nid: nid == "node-a")  # a mandate admits only node-a
    assert set(fed.node_ids) == {"node-a"}
    with pytest.raises(KeyError):
        fed.node("node-b")  # node-b was never admitted to this federation view


# ---- honest: a node that moved reads as drift, never silently stale --------------------------

def test_verify_federated_flags_a_node_that_moved():
    fed = federated_view(_STATES)
    current = {"node-a": _STATES["node-a"], "node-b": {"posture": "aligned", "secret": "b-only", "balance": 999}}
    status = verify_federated(fed, current)
    assert status["node-a"].fresh and not status["node-a"].drift
    assert status["node-b"].drift and not status["node-b"].fresh


def test_verify_federated_flags_a_departed_node_as_drift():
    fed = federated_view(_STATES)
    status = verify_federated(fed, {"node-a": _STATES["node-a"]})  # node-b no longer reporting
    assert status["node-b"].drift  # its rendered view can no longer be confirmed — honest, not hidden


# ---- composition boundary: composes the Lens by identity --------------------------------------

def test_composes_the_lens_by_identity():
    from sovereign_agent.sovereign_ux import federated_view as fv
    from sovereign_agent.sovereign_ux.lens import render_view as rv, verify_view as vv
    assert fv.render_view is rv and fv.verify_view is vv  # composes V01, not a re-implementation


def test_empty_federation_owns_nothing():
    fed = federated_view({})
    assert fed.node_ids == ()  # no nodes, no owned state — a federation surface that composes nothing yet
