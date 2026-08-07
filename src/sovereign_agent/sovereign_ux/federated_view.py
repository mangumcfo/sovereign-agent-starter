# -*- coding: utf-8 -*-
"""sovereign_ux.federated_view — Federation UX (S8 Vol 6).

`federated_view` renders a **scoped, read-only view across multiple sovereign nodes** — each node
supplies its own governed snapshot, and the federation surface renders each through the Sovereign Lens
(V01 `render_view`) into a frozen composite. It **renders cross-node state and owns no cross-node
authority**: nothing here reaches into a node, commands it, or mutates it — each node stays sovereign,
supplying its own state. It exposes **no write path** — the federation surface cannot act on a node;
to act, compose that node's Atrium (S8 Vol 4), whose write routes through the breath-gate (S8 Vol 2).

Kill-targets: **renders cross-node state, owns no cross-node authority** (renders supplied snapshots,
never fetches or commands) · **each node sovereign** (read-only; a node's state is never mutated) ·
**no central federation console** (a render + frozen composite, no write/act method) · **writes only
through V02's gate** (no write path here; action composes the Atrium). Composes the Sovereign Lens (S8
Vol 1) directly; the cross-node substrate it renders is delivered by the sealed inter-node floors it
composes at the volume level — Resonance Coordination (S6 Vol 4), Collaboration (S6 Vol 2), Receipted
Inter-Node Messaging (S6 Vol 1); transport is OUT (the Sovereign Port, S6 Vol 7). **Rolls no
cryptography.**
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence

from .lens import render_view, verify_view, View, ViewStatus   # V01 The Sovereign Lens

__all__ = ["FederatedView", "federated_view", "verify_federated"]


@dataclass(frozen=True)
class FederatedView:
    """A frozen, read-only composite of per-node Lens Views — the federation surface across sovereign
    nodes. It holds each node's rendered View keyed by node id, owns no cross-node authority, and
    exposes NO method that acts on or mutates a node."""
    views: Mapping[str, View]

    @property
    def node_ids(self) -> tuple:
        """The sovereign nodes present in this view (those the mandate admitted)."""
        return tuple(self.views.keys())

    def node(self, node_id: str) -> View:
        """The read-only Lens View of one node's admitted state."""
        return self.views[node_id]


def federated_view(node_states: Mapping[str, Any], *, mandate: Optional[str] = None,
                   scope: Optional[Mapping[str, Sequence[str]]] = None,
                   admits: Optional[Callable[[str], bool]] = None) -> FederatedView:
    """Render a scoped, read-only view across multiple sovereign nodes.

    `node_states` is ``{node_id: that node's SUPPLIED governed snapshot}`` — each node supplies its own
    state; nothing here reaches into a node, commands it, or mutates it. Each snapshot is rendered
    through the Sovereign Lens (`render_view`), mandate-scoped (S5 Vol 28, deny-by-default), and
    assembled into a frozen `FederatedView`. Optionally `admits(node_id)` scopes WHICH nodes the mandate
    may see (deny-by-default is the caller's to express). Renders cross-node state; owns no cross-node
    authority; no write path. Rolls no cryptography."""
    admitted = node_states
    if admits is not None:
        admitted = {nid: snap for nid, snap in node_states.items() if admits(nid)}  # a mandate admits which NODES
    views = {nid: render_view(snap, mandate=mandate, scope=scope) for nid, snap in admitted.items()}
    return FederatedView(views=dict(views))


def verify_federated(fed: FederatedView, current_states: Mapping[str, Any]) -> dict:
    """Per-node freshness of a `FederatedView` against the nodes' current supplied states — honest,
    never silently stale. A node whose state moved since render reads as **drift**; a node no longer
    present in `current_states` also reads as drift (its rendered view can no longer be confirmed).
    Returns ``{node_id: ViewStatus}``."""
    out = {}
    for nid, view in fed.views.items():
        if nid in current_states:
            out[nid] = verify_view(view, current_states[nid])
        else:
            out[nid] = ViewStatus(fresh=False, drift=True,
                                  rendered_fingerprint=view.fingerprint, current_fingerprint="")
    return out
