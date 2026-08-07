# -*- coding: utf-8 -*-
"""Acceptance tests for Breath-Gated Interfaces (S8 Vol 2) — gate_interaction.

Proves: propose opens a DRAFT (never applies) · review reads the ledger-backed pending · dispose is
human-gated (AH-1: a gate-less ledger denies a material obligation) and mandate-scoped (S5 Vol 28,
deny-by-default) · a rejection needs no gate · the session-scoped view is honestly empty (the honesty
boundary). Composes the sealed ObligationLedger + mandate_guard. Crypto-free.
"""
import pytest

from sovereign_agent.sovereign_ux.gate_interaction import (
    propose, review, dispose, session_view, GateDenied, SESSION_VIEW_NOTE,
)
from sovereign_agent.obligations.ledger import ObligationLedger


def _ledger(tmp_path, gate=None):
    return ObligationLedger(root=tmp_path / "obl", gate=gate)


def _approving_gate(action, obligation):
    return {"status": "approved"}


def _denying_gate(action, obligation):
    return {"status": "denied"}


# ---- propose / review (the write is never applied by the surface) ----------------------------

def test_propose_opens_a_draft_and_review_lists_it(tmp_path):
    L = _ledger(tmp_path)
    oid = propose(L, "rename the ridgeline ledger label")
    assert isinstance(oid, str) and oid
    pending = review(L)
    assert any((e.get("id") or e.get("obligation_id")) == oid for e in pending)


def test_review_shrinks_when_an_obligation_is_disposed(tmp_path):
    L = _ledger(tmp_path, gate=_approving_gate)
    a = propose(L, "action A", material=True)
    b = propose(L, "action B", material=True)
    assert len(review(L)) == 2
    dispose(L, a, approver="operator", evidence="applied; artifact /ridgeline/label.txt updated")
    assert len(review(L)) == 1


# ---- dispose: human breath-gate (AH-1 deny-by-default) ---------------------------------------

def test_material_dispose_without_a_gate_is_denied(tmp_path):
    L = _ledger(tmp_path)  # NO gate injected
    oid = propose(L, "materially binding action", material=True)
    with pytest.raises(GateDenied):
        dispose(L, oid, approver="operator", evidence="artifact path present")


def test_material_dispose_with_an_approving_gate_closes(tmp_path):
    L = _ledger(tmp_path, gate=_approving_gate)
    oid = propose(L, "materially binding action", material=True)
    result = dispose(L, oid, approver="operator", evidence="applied; artifact /ridgeline/x.txt present")
    assert result  # closed with a receipt
    assert not any((e.get("id") or e.get("obligation_id")) == oid for e in review(L))


def test_denying_gate_bars_the_disposition(tmp_path):
    L = _ledger(tmp_path, gate=_denying_gate)
    oid = propose(L, "materially binding action", material=True)
    with pytest.raises(GateDenied):
        dispose(L, oid, approver="operator", evidence="artifact present")


# ---- dispose: mandate scope (S5 Vol 28, deny-by-default) --------------------------------------

def test_scoped_mandate_wrong_mandate_is_barred(tmp_path):
    L = _ledger(tmp_path, gate=_approving_gate)
    oid = propose(L, "treasury-scoped action", material=True, mandate="treasury")
    with pytest.raises(GateDenied):
        dispose(L, oid, approver="auditor", held_mandates=["audit"],
                evidence="artifact present")  # approver does NOT hold 'treasury'


def test_scoped_mandate_correct_mandate_passes(tmp_path):
    L = _ledger(tmp_path, gate=_approving_gate)
    oid = propose(L, "treasury-scoped action", material=True, mandate="treasury")
    result = dispose(L, oid, approver="treasurer", held_mandates=["treasury"],
                     evidence="applied; artifact /ridgeline/treasury.txt present")
    assert result
    assert not any((e.get("id") or e.get("obligation_id")) == oid for e in review(L))


# ---- a refusal needs no gate -----------------------------------------------------------------

def test_reject_needs_no_gate(tmp_path):
    L = _ledger(tmp_path)  # gate-less, yet a 'no' is always allowed
    oid = propose(L, "materially binding action", material=True)
    result = dispose(L, oid, approver="operator", reject=True, evidence="declined by the operator")
    assert result
    assert not any((e.get("id") or e.get("obligation_id")) == oid for e in review(L))


# ---- the honesty boundary: session-scoped view is honestly empty -----------------------------

def test_session_view_is_honestly_empty(tmp_path):
    v = session_view()
    assert v["scope"] == "session" and v["persists"] is False and v["pending"] == []
    assert "Empty is honest" in v["note"] and "ledger-backed" in v["note"]


def test_session_view_names_the_ledger_as_the_constitutional_gate(tmp_path):
    v = session_view([{"id": "x"}])
    assert v["persists"] is False  # even holding items, it persists nothing
    assert "ledger" in v["constitutional_gate"].lower()
    assert SESSION_VIEW_NOTE == v["note"]


# ---- composition boundary --------------------------------------------------------------------

def test_composes_sealed_ledger_and_mandate_guard():
    from sovereign_agent.sovereign_ux import gate_interaction as gi
    from sovereign_agent.obligations.ledger import ObligationLedger as L2
    from sovereign_agent.obligations import mandate_guard as mg2
    assert gi.ObligationLedger is L2      # the ledger-backed gate is composed, not re-implemented
    assert gi.mandate_guard is mg2        # the S5 Vol 28 scoping principal is composed
