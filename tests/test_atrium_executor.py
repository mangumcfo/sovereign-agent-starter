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
