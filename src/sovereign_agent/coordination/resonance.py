"""Resonance coordination — nodes coordinate by reconciling independently-computed state, not by central control.

Co-extrusion for s6_04 (Resonance Coordination, KM S6 wave 2026-08-05). Pure / structural, no crypto substrate beyond
the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). Sovereign nodes coordinate WITHOUT a central
controller: each node computes its own coordination signal -- the integrity root over its governed state -- for itself,
and two nodes coordinate by comparing those independently-computed signals. They resonate when the signals agree; when
they differ, the divergence is surfaced for governance rather than silently reconciled to one side. No central truth:
neither node's state is authoritative over the other, so coordination is mutual agreement (or a flagged divergence),
never one node's state overwriting another's or a controller dictating alignment.

Two governed acts:
  * `node_signal` computes a node's coordination signal -- its own integrity root over exactly its mandate's governed
    objects -- composing the sealed Federation Node Governance `node_root`. Two nodes compute this INDEPENDENTLY; neither
    signal is authoritative over the other.
  * `resonate` reconciles two nodes by comparing their independently-computed signals -- composing the sealed
    Federation Node Governance `reconcile_roots`: agree, and the nodes are RESONANT (coordinated on shared state);
    differ, and the divergence is surfaced for governance, neither node's state authoritative. There is no central
    controller: coordination is the mutual agreement of two independently-computed signals, or an honest flag that they
    have diverged -- never central control.

Human primacy and the sovereignty boundary hold: each node's signal is its own, and coordination is agreement between
equals, not a command from a center. This module builds no coordination server, no central controller, no consensus
engine, and no orchestrator of its own -- the node signal is the sealed Federation Node Governance floor's, and the
reconciliation is the sealed floor's mutual-agreement check, composed."""
from __future__ import annotations

from typing import Dict

from ..federation.node_gov import node_root, reconcile_roots


class CoordinationError(ValueError):
    """Raised when a coordination signal cannot be computed honestly: a node with no mandate to root over -- fail-closed,
    a node's coordination signal is its own governed state root, and coordination is mutual agreement of independently-
    computed signals, never central control."""


def node_signal(reg, mandate: str) -> str:
    """Compute a node's coordination signal -- its own integrity root over exactly its mandate's governed objects --
    composing the sealed Federation Node Governance `node_root`. Two nodes compute this INDEPENDENTLY and compare it
    (`resonate`); neither node's signal is authoritative over the other. Refuses an empty mandate -- a node signal roots
    over a real mandate's objects, never an unscoped whole."""
    if not str(mandate).strip():
        raise CoordinationError("a node signal needs a mandate to root over")
    return node_root(reg, mandate)


def resonate(node_signal_value: str, peer_signal_value: str) -> Dict[str, object]:
    """Reconcile two nodes by comparing their INDEPENDENTLY-computed coordination signals -- composing the sealed
    Federation Node Governance `reconcile_roots`. Agree, and the nodes are RESONANT (coordinated on shared state);
    differ, and the divergence is surfaced for governance rather than silently reconciled to one side. No central truth:
    neither signal is authoritative, so coordination is mutual agreement (or a flagged divergence), never one node's
    state overwriting another's or a controller dictating alignment. Returns whether the nodes are resonant, both
    signals, and any divergence."""
    result = reconcile_roots(node_signal_value, peer_signal_value)
    return {
        "resonant": bool(result["aligned"]),
        "node_signal": result["node_root"],
        "peer_signal": result["peer_root"],
        "divergence": result["divergence"],
    }
