"""Acceptance tests for Resonance Coordination (s6_04, S6 Vol 4) — nodes coordinate by reconciling independently-computed
state, not by central control, composing the sealed Federation Node Governance node_root + reconcile_roots. Pure (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.coordination.resonance import node_signal, resonate, CoordinationError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def test_node_signal_is_the_nodes_own_root(tmp_path):
    reg = _reg(tmp_path)
    reg.append("obj:1", {"v": 1}, author="nodeA", source_ref="s://a/1", at="t", mandate="nodeA", kind="ratify")
    sig = node_signal(reg, "nodeA")
    assert isinstance(sig, str) and len(sig) == 64  # a hash root


def test_node_signal_refuses_empty_mandate(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(CoordinationError):
        node_signal(reg, "  ")


def test_resonate_true_when_signals_agree():
    res = resonate("abc123", "abc123")
    assert res["resonant"] is True
    assert res["divergence"] is None


def test_resonate_false_and_surfaces_divergence_when_signals_differ():
    res = resonate("abc123", "def456")
    assert res["resonant"] is False
    assert res["divergence"] is not None
    assert res["node_signal"] == "abc123" and res["peer_signal"] == "def456"


def test_two_nodes_with_identical_state_resonate(tmp_path, tmp_path_factory):
    a = ObjectRegistry(str(tmp_path_factory.mktemp("a")))
    b = ObjectRegistry(str(tmp_path_factory.mktemp("b")))
    for reg in (a, b):
        reg.append("shared:1", {"v": 1}, author="n", source_ref="s://n/1", at="t", mandate="fed", kind="ratify")
    res = resonate(node_signal(a, "fed"), node_signal(b, "fed"))
    assert res["resonant"] is True


def test_two_nodes_with_divergent_state_do_not_resonate(tmp_path_factory):
    a = ObjectRegistry(str(tmp_path_factory.mktemp("a")))
    b = ObjectRegistry(str(tmp_path_factory.mktemp("b")))
    a.append("shared:1", {"v": 1}, author="n", source_ref="s://n/1", at="t", mandate="fed", kind="ratify")
    b.append("shared:1", {"v": 2}, author="n", source_ref="s://n/2", at="t", mandate="fed", kind="ratify")
    res = resonate(node_signal(a, "fed"), node_signal(b, "fed"))
    assert res["resonant"] is False
    assert res["divergence"] is not None
