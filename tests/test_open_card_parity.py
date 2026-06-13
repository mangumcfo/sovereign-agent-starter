"""Open Card Parity harness tests — audit 2026-06-13 Phase C.

The harness is the INVARIANT that kills the "view out-truthing the ledger" class (KM's 42 dropped
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
    return ObligationLedger(root=str(tmp_path / "obligations"), principal_id="KM-1176")


def test_parity_holds_on_clean_ledger(tmp_path):
    led = _ledger(tmp_path)
    a = led.open("feedback: fix ch3", owner="KM-1176")["id"]
    led.open("feedback: fix ch4", owner="KM-1176")
    led.close(a, evidence="E1: /tmp/x done", require_e1=False)
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert res["ok"], res["violations"]
    assert res["summary"] == {"open": 1, "closed": 1, "total": 2}


def test_parity_and_by_owner_survive_reopen(tmp_path):
    """The old by_owner() derived 'closed' from raw credits, so a reopened card double-counted. Parity
    must hold and by_owner must count a reopened card OPEN."""
    led = _ledger(tmp_path)
    oid = led.open("feedback: cross-foot", owner="KM-1176")["id"]
    led.close(oid, evidence="E1: /tmp/done", require_e1=False)
    led.reopen(oid, reason="reopened by incident — closed without disposition")
    bo = led.by_owner()
    assert bo["KM-1176"]["open"] == 1 and bo["KM-1176"]["closed"] == 0
    assert led._is_closed(oid) is False
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert res["ok"], res["violations"]


def test_harness_detects_a_broken_view(tmp_path, monkeypatch):
    """If a view (here by_owner) disagrees with replay, the harness must FAIL — that is its whole job."""
    led = _ledger(tmp_path)
    led.open("feedback: ch5", owner="KM-1176")
    # break by_owner so its open-sum no longer matches replay
    monkeypatch.setattr(led, "by_owner", lambda: {"KM-1176": {"open": 99, "closed": 0}})
    res = ocp.check_parity(tmp_path / "obligations", led=led)
    assert not res["ok"]
    assert any("by_owner" in v for v in res["violations"])


def test_live_atrium_review_chain_holds_parity():
    """Smoke: the LIVE review chain must hold parity (the deliverable verification)."""
    root = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "atrium_review"
    if not (root / "obligations.ndjson").exists():
        pytest.skip("no live atrium_review chain on this host")
    res = ocp.check_parity(root)
    assert res["ok"], res["violations"]
