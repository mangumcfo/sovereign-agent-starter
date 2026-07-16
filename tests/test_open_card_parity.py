"""Open Card Parity harness tests — audit 2026-06-13 Phase C.

The harness is the INVARIANT that kills the "view out-truthing the ledger" class (the operator's 42 dropped
comments). These tests prove: (1) parity holds on a clean ledger, (2) parity SURVIVES a reopen — the
exact case the old by_owner() double-counted, (3) the harness actually DETECTS a broken view.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import open_card_parity as ocp  # noqa: E402
from sovereign_agent.obligations.ledger import ObligationLedger  # noqa: E402


def _ledger(tmp_path):
    return ObligationLedger(root=str(tmp_path / "obligations"), principal_id="owner")


def test_parity_holds_on_clean_ledger(tmp_path):
    led = _ledger(tmp_path)
    a = led.open("feedback: fix ch3", owner="owner")["id"]
    led.open("feedback: fix ch4", owner="owner")
    led.close(a, evidence="E1: /tmp/x done", require_e1=False)
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert res["ok"], res["violations"]
    assert res["summary"] == {"open": 1, "closed": 1, "total": 2}


def test_parity_and_by_owner_survive_reopen(tmp_path):
    """The old by_owner() derived 'closed' from raw credits, so a reopened card double-counted. Parity
    must hold and by_owner must count a reopened card OPEN."""
    led = _ledger(tmp_path)
    oid = led.open("feedback: cross-foot", owner="owner")["id"]
    led.close(oid, evidence="E1: /tmp/done", require_e1=False)
    led.reopen(oid, reason="reopened by incident — closed without disposition")
    bo = led.by_owner()
    assert bo["owner"]["open"] == 1 and bo["owner"]["closed"] == 0
    assert led._is_closed(oid) is False
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert res["ok"], res["violations"]


def test_harness_detects_a_broken_view(tmp_path, monkeypatch):
    """If a view (here by_owner) disagrees with replay, the harness must FAIL — that is its whole job."""
    led = _ledger(tmp_path)
    led.open("feedback: ch5", owner="owner")
    # break by_owner so its open-sum no longer matches replay
    monkeypatch.setattr(led, "by_owner", lambda: {"owner": {"open": 99, "closed": 0}})
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert not res["ok"]
    assert any("by_owner" in v for v in res["violations"])


def test_review_chain_holds_parity(tmp_path):
    """Smoke: a review chain must hold parity (the deliverable verification).
    Runs against the LIVE chain when this host carries one; otherwise builds a
    real fixture chain and verifies THAT — the zero-skip law means this proof
    executes everywhere, never silently dropping coverage on clean checkouts."""
    root = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "atrium_review"
    if not (root / "obligations.ndjson").exists():
        led = _ledger(tmp_path)  # fixture chain: open -> close with evidence
        oid = led.open("review: fixture card", owner="reviewer")["id"]
        led.close(oid, evidence="fixture evidence path", evidence_tier="E1",
                  closed_by="reviewer")
        root = tmp_path / "obligations"
    res = ocp.check_parity(root)
    assert res["ok"], res["violations"]
