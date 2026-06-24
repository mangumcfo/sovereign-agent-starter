"""The BELL — atrium_executor — audit 2026-06-13d #4 (was zero-coverage).

The second half of feedback-accept: execute() routes a packet by ref-class, closing scriptable classes
(distribution/b12/editorial_r1) with an E2 receipt and handshaking agent/unregistered classes (obligation
stays open). drain() executes only approved-and-open. These tests drive it on a TMP ledger root.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import atrium_executor as E  # noqa: E402
from sovereign_agent.obligations.ledger import ObligationLedger  # noqa: E402


@pytest.fixture
def led(tmp_path, monkeypatch):
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.setenv("HANDSHAKES_STORE", str(tmp_path / "handshakes.json"))
    monkeypatch.delenv("BREATHLINE_EXECUTOR_AGENT", raising=False)
    return ObligationLedger(root=str(tmp_path / "obligations"), principal_id="KM-1176")


def _fresh(led):
    return ObligationLedger(root=str(led.root))   # cold read of the same chain


def test_scriptable_class_closes_with_receipt(led):
    ob = led.open("distribution packet", ref="distribution:b12", classification="C2")
    assert E.execute(ob["id"]) == 0
    after = _fresh(led)
    assert after._is_closed(ob["id"]) is True
    credit = next(e for e in after.iter_entries() if e.get("type") == "credit" and e.get("closes") == ob["id"])
    assert credit["receipt"]["evidence_tier"] == "E2"


def test_b12_and_editorial_classes_close(led):
    for ref in ("b12:republish", "editorial_r1:format"):
        ob = led.open(f"pkt {ref}", ref=ref, classification="C2")
        assert E.execute(ob["id"]) == 0
        assert _fresh(led)._is_closed(ob["id"]) is True


def test_unregistered_class_handshakes_not_closed(led, tmp_path):
    ob = led.open("mystery packet", ref="weirdclass:x", classification="C2")
    assert E.execute(ob["id"]) == 0
    assert _fresh(led)._is_closed(ob["id"]) is False          # NOT closed
    assert (tmp_path / "handshakes.json").exists()            # residue recorded, never silently stuck


def test_agent_class_handshakes_not_closed(led):
    ob = led.open("board finding", ref="board_finding:ch3", classification="C2")
    assert E.execute(ob["id"]) == 0
    assert _fresh(led)._is_closed(ob["id"]) is False


def test_missing_and_already_closed(led):
    assert E.execute("obl_does_not_exist") == 1               # missing → 1
    ob = led.open("dist", ref="distribution:b12", classification="C2")
    assert E.execute(ob["id"]) == 0                           # closes
    assert E.execute(ob["id"]) == 0                           # already closed → 0 (no double-close)


def test_drain_only_approved_and_open(led):
    approved = led.open("approved dist", ref="distribution:b12", classification="C2")
    led.approve(approved["id"], approved_by="KM-1176")
    unapproved = led.open("pending dist", ref="distribution:b12", classification="C2")
    assert E.drain() == 0
    after = _fresh(led)
    assert after._is_closed(approved["id"]) is True           # approved+open → executed (closed)
    assert after._is_closed(unapproved["id"]) is False        # not approved → left open


def test_close_failure_is_not_a_false_success(led, tmp_path, monkeypatch):
    """Engine 95+ HIGH #4 (card cd010960): when the ledger close FAILS at commit time, the scriptable
    executor must NOT report success. It returns non-zero, the obligation stays visibly OPEN, and an
    apply_close_failed handshake records the residue — the false-close that exited 0 is gone."""
    import json

    from sovereign_agent.obligations.ledger import ObligationLedger as OL

    ob = led.open("distribution packet", ref="distribution:b12", classification="C2")

    def boom(self, *a, **k):  # simulate a commit/disk failure inside ledger.close
        raise RuntimeError("simulated ledger commit failure")

    monkeypatch.setattr(OL, "close", boom)

    rc = E.execute(ob["id"])
    assert rc == 1                                            # NOT a false 0 (the bug)
    after = _fresh(led)
    assert after._is_closed(ob["id"]) is False               # obligation stays OPEN, never falsely closed
    hs = json.loads((tmp_path / "handshakes.json").read_text())
    assert any(h.get("status") == "apply_close_failed" for h in hs)   # residue is visible, not swallowed


def _fake_scheduler(monkeypatch, ret):
    """Inject a fake `scheduler` module so _exec_distribution_launch's call-time `from scheduler import dispatch`
    picks up a stub returning `ret` — lets us drive the bell against the REAL list-shaped dispatch return."""
    import types
    mod = types.ModuleType("scheduler")
    mod.dispatch = lambda book_id, dry_run=True: ret
    monkeypatch.setitem(sys.modules, "scheduler", mod)


def test_distribution_launch_closes_on_list_shaped_dispatch(led, monkeypatch):
    """Audit HIGH [491] 2026-06-24: dispatch() returns `results` as a LIST of {channel,...} dicts, not a dict.
    The old handler called .keys() on it OUTSIDE the try → posted LIVE then threw, obligation never closed
    (a false failure on an approved launch). The bell must name the channels from the list and close E2."""
    _fake_scheduler(monkeypatch, {
        "book_id": "01_strategic_finance", "mode": "live", "approved_by": "KM-1176",
        "results": [
            {"channel": "x", "ok": True, "live": True, "detail": "posted"},
            {"channel": "linkedin", "ok": True, "live": True, "detail": "posted"},
        ],
    })
    ob = led.open("launch pkt", ref="distribution_launch:01_strategic_finance", classification="C2")
    assert E.execute(ob["id"]) == 0                               # no crash on the list (was the bug)
    after = _fresh(led)
    assert after._is_closed(ob["id"]) is True                    # approved launch closes (no false failure)
    credit = next(e for e in after.iter_entries() if e.get("type") == "credit" and e.get("closes") == ob["id"])
    assert credit["receipt"]["evidence_tier"] == "E2"
    assert "linkedin,x" in credit["receipt"]["evidence"]         # channels named from the LIST, sorted


def test_distribution_launch_refused_stays_open(led, tmp_path, monkeypatch):
    """The constitutional gate signals refusal in the RETURN ({refused:True}), not by raising — and a refusal
    still carries mode='live'. The bell must detect refused FIRST, leave the obligation OPEN, and record a
    blocked_unapproved residue — never a silent green that implies a post happened."""
    import json
    _fake_scheduler(monkeypatch, {
        "book_id": "01_strategic_finance", "mode": "live", "refused": True,
        "reason": "launch obligation NOT approved", "results": [
            {"channel": "x", "ok": False, "live": False, "detail": "REFUSED (ungated)"},
        ],
    })
    ob = led.open("launch pkt", ref="distribution_launch:01_strategic_finance", classification="C2")
    assert E.execute(ob["id"]) == 1                              # refused → non-zero, not a false success
    after = _fresh(led)
    assert after._is_closed(ob["id"]) is False                  # stays OPEN — nothing posted, nothing closed
    hs = json.loads((tmp_path / "handshakes.json").read_text())
    assert any(h.get("status") == "blocked_unapproved" for h in hs)


def test_execute_refuses_unapproved_material(led, tmp_path):
    """Engine 95+ #4b-ii fail-fast: a MATERIAL obligation that hasn't cleared the breath-gate is refused at
    execute() top (returns 1, stays OPEN, blocked_unapproved residue) — defense-in-depth ahead of the
    downstream ledger.close() gate. Non-material packets are unaffected (covered by the other tests)."""
    import json

    ob = led.open("material packet", ref="distribution:b12", classification="C2", material=True)
    rc = E.execute(ob["id"])
    assert rc == 1                                           # refused, not a false success
    after = _fresh(led)
    assert after._is_closed(ob["id"]) is False              # stays OPEN — never executed unapproved
    hs = json.loads((tmp_path / "handshakes.json").read_text())
    assert any(h.get("status") == "blocked_unapproved" for h in hs)
