"""
Singleton wiring of the Python core for the Node API process.

The Node API serves one sovereign node per process. We boot a single
`UniversalSovereignNode` at server start and reuse it across requests.
This honours the "one node, one identity, one audit chain" discipline
(Principle 1 — Human Primacy & Sovereign Agency).

Tests + dev mode can override via `set_node()`.
"""

from __future__ import annotations

import os
from typing import Optional

from ..universal_sovereign_node import UniversalSovereignNode
from ..compliance.human_approval_gate import HumanApprovalGate


_NODE: Optional[UniversalSovereignNode] = None
_APPROVAL_GATE: Optional[HumanApprovalGate] = None


def get_node() -> UniversalSovereignNode:
    """Return the process-wide singleton node, instantiating on first call."""
    global _NODE
    if _NODE is None:
        context = os.environ.get("BREATHLINE_NODE_CONTEXT", "personal")
        name = os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode")
        _NODE = UniversalSovereignNode(name=name, context_type=context)
    return _NODE


def get_approval_gate() -> HumanApprovalGate:
    """
    Return the process-wide breath-gate (HumanApprovalGate) singleton.

    The core `ComplianceEngine` does not hold a persistent pending-approvals
    store (its `request_human_approval` is a stateless sim hook). The Node API
    provides one real, in-memory, **session-scoped** store so the breath-gate
    endpoints (D) operate on actual state. It is legitimately EMPTY on a fresh
    node until a regulated action triggers `requires_approval` — that empty
    state is the honest truth, not a stub.
    """
    global _APPROVAL_GATE
    if _APPROVAL_GATE is None:
        _APPROVAL_GATE = HumanApprovalGate()
    return _APPROVAL_GATE


_LEDGER = None


def get_obligation_ledger():
    """Return the process-wide ObligationLedger (R-23), wired to this node's breath-gate +
    ComplianceEngine. Node-local storage root (boundary guard applies); never the live seal chain.

    Dev note: wired with simulate_gate=True — a material obligation's approval is a simulated human
    disposition. Production routes approval to an external workflow (honest, labeled)."""
    global _LEDGER
    if _LEDGER is None:
        from ..obligations.node_integration import wire_node_ledger
        _LEDGER = wire_node_ledger(
            root=os.environ.get("OBLIGATION_LEDGER_ROOT"),  # None -> ledger default (node-local)
            node=get_node(),
            mode=os.environ.get("BREATHLINE_NODE_MODE", "sovereign"),
            simulate_gate=True,
        )
    return _LEDGER


def set_node(node: UniversalSovereignNode) -> None:
    """Override the singleton (tests / dev)."""
    global _NODE
    _NODE = node


def reset_node() -> None:
    """Drop the singletons (tests)."""
    global _NODE, _APPROVAL_GATE, _LEDGER
    _NODE = None
    _APPROVAL_GATE = None
    _LEDGER = None
