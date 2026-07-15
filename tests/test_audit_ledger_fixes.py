"""Regression tests for the audit quick-wins on the ObligationLedger (2026-06-10)."""
import json

import pytest

from sovereign_agent.obligations import ObligationLedger, AlreadyClosedError


def test_denied_approval_does_not_read_as_approved(tmp_path):
    """replay()/full_log() must honor disposition — a denied approval cannot flip a draft to approved."""
    led = ObligationLedger(str(tmp_path), principal_id="node")
    ob = led.open(title="needs review", classification="C2", material=True)
    oid = ob["id"]
    # Append a DENIED approval entry directly (no gate wired in this standalone ledger).
    led._append({"type": "approval", "id": "ap1", "approves": oid,
                 "approved_by": "node", "disposition": "denied", "principal_id": "node"})

    replay = led.replay()
    drafted = {o["id"]: o for o in replay["all"]}
    assert drafted[oid].get("approved") is not True, "denied approval wrongly read as approved in replay()"

    fl = {o["id"]: o for o in led.full_log()}
    assert fl[oid].get("approved") is False, "denied approval wrongly read as approved in full_log()"
    assert fl[oid].get("disposition") == "denied"


def test_close_nonexistent_raises_keyerror(tmp_path):
    led = ObligationLedger(str(tmp_path), principal_id="node")
    with pytest.raises(KeyError):
        led.close("obl_does_not_exist", evidence="artifacts/x.md", evidence_tier="E1")


def test_double_close_raises_already_closed(tmp_path):
    led = ObligationLedger(str(tmp_path), principal_id="node")
    ob = led.open(title="x", classification="C2")
    led.close(ob["id"], evidence="artifacts/x.md", evidence_tier="E1")
    with pytest.raises(AlreadyClosedError):
        led.close(ob["id"], evidence="artifacts/x.md", evidence_tier="E1")


def test_approve_nonexistent_raises_keyerror(tmp_path):
    led = ObligationLedger(str(tmp_path), principal_id="node")
    with pytest.raises(KeyError):
        led.approve("obl_nope", approved_by="node")


def test_entries_cache_invalidates_on_append(tmp_path):
    """The parse-cache must re-read after a write (mtime/size change), never serve a stale view."""
    led = ObligationLedger(str(tmp_path), principal_id="node")
    led.open(title="a", classification="C2")
    assert len(led._entries()) == 1
    led.open(title="b", classification="C2")  # mtime/size change → cache invalidates
    assert len(led._entries()) == 2
    assert led.verify_chain() is True
