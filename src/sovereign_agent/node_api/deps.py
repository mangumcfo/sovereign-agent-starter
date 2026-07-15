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

    Breath-gate is REAL in every mode (audit 2026-06-11, real_gates_every_mode): a material obligation's
    approval records the AUTHENTICATED principal who called /approve — never a simulated disposition. Set
    BREATHLINE_GATE_MODE=external only when approval arrives via an out-of-band workflow (then the gate
    returns 'pending' and the obligation is not closeable until the real disposition lands)."""
    global _LEDGER
    if _LEDGER is None:
        from ..obligations.node_integration import wire_node_ledger
        from ..obligations.ledger import get_ledger_root
        # ONE resolver (audit 2026-06-13): env → canonical atrium_review. Never the empty parent default
        # that produced the API↔executor split-brain (approve in one chain, close in another).
        root = str(get_ledger_root())
        _assert_root_not_starved(root)  # THREAD [245] + audit 2026-06-13: REFUSE an empty root beside a rich sibling
        _LEDGER = wire_node_ledger(
            root=root,
            node=get_node(),
            mode=os.environ.get("BREATHLINE_NODE_MODE", "sovereign"),
            gate_mode=os.environ.get("BREATHLINE_GATE_MODE", "sovereign"),
        )
    return _LEDGER


def _assert_root_not_starved(root):
    """Serve refusal (audit 2026-06-13, escalated from log-only; THREAD [245] principle 4): if the served
    ledger root is EMPTY while a sibling root under memory/obligations/* holds real cards, REFUSE — never
    render a clean-looking empty queue while real work sits in a sibling. The exact failure that silently
    hid the operator's 42 cards. A computation error in the guard never blocks boot; only a *confirmed* starvation
    raises."""
    import logging
    from pathlib import Path
    from ..obligations.ledger import get_ledger_root  # THE one resolver (Universalize Wave §2/G3)
    log = logging.getLogger("breathline.ledger")
    try:
        served = Path(root).expanduser() if root else get_ledger_root()
        sf = served / "obligations.ndjson"
        served_n = sum(1 for _ in sf.open()) if sf.exists() else 0
        base = served.parent if served.name != "obligations" else served
        siblings = {sib.parent.name: sum(1 for _ in sib.open())
                    for sib in base.glob("*/obligations.ndjson")
                    if sib.parent.resolve() != served.resolve()}
        richest = max(siblings.values(), default=0)
    except Exception as exc:  # never let a guard-computation error break boot
        log.warning("ledger-starvation guard skipped: %s", exc)
        return
    if served_n == 0 and richest > 10:
        who = max(siblings, key=siblings.get)
        raise RuntimeError(
            f"LEDGER STARVED: served root {served} is EMPTY while sibling '{who}' holds {richest} "
            f"packets. Refusing to serve a silently-empty queue while real work sits in a sibling — "
            f"set OBLIGATION_LEDGER_ROOT correctly.")


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
