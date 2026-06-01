"""Acceptance tests for the node ObligationLedger (R-23 Phase 1).

Maps to the acceptance bar in R23_MAKE_B32_REAL_PLAN §5. Phase-2+ items (node breath-gate
wiring, Node API, Atrium lens) are tested in their own phases.
"""
import json
import os

import pytest

from sovereign_agent.obligations import (
    ObligationLedger,
    classify_evidence,
    EvidenceTier,
    LedgerBoundaryError,
)


def test_open_close_mints_receipt_and_state(tmp_path):
    """#1: open -> close(E2) -> receipt minted; obligation shows closed."""
    led = ObligationLedger(root=tmp_path, principal_id="node")
    ob = led.open("Wire B32 obligations to the node", owner="tiger")
    assert ob["type"] == "debit" and ob["draft"] is True  # CYL-006
    led.approve(ob["id"], approved_by="km-1176")
    credit = led.close(ob["id"], evidence="commit a1b2c3d4e5f60718 /repo/file.py", closed_by="tiger")
    assert credit["type"] == "credit"
    assert credit["receipt"]["receipt_id"].startswith("rcpt_")
    assert credit["evidence_tier"] == "E2"  # hash + path => E2
    st = led.replay()
    assert any(o["id"] == ob["id"] for o in st["closed"])
    assert not any(o["id"] == ob["id"] for o in st["open"])


def test_replay_reproduces_state(tmp_path):
    """#2: a fresh ledger on the same root replays to the same state."""
    led = ObligationLedger(root=tmp_path)
    a = led.open("A")
    led.open("B")
    led.close(a["id"], evidence="~/proof.json")  # E1
    led2 = ObligationLedger(root=tmp_path)  # reopen
    assert led2.by_status() == {"open": 1, "closed": 1, "total": 2}


def test_e0_rejected_for_material_close(tmp_path):
    """#3: claim-only evidence (E0) is rejected when require_e1 (default)."""
    led = ObligationLedger(root=tmp_path)
    ob = led.open("X")
    with pytest.raises(ValueError):
        led.close(ob["id"], evidence="done")  # no artifact -> E0
    # explicit override allows it (non-material path)
    credit = led.close(ob["id"], evidence="done", require_e1=False)
    assert credit["evidence_tier"] == "E0"


def test_chain_integrity(tmp_path):
    """#4: hash chain verifies; tampering breaks it."""
    led = ObligationLedger(root=tmp_path)
    led.open("one")
    led.open("two")
    assert led.verify_chain() is True
    # tamper a line
    lines = led.path.read_text().splitlines()
    rec = json.loads(lines[0]); rec["title"] = "TAMPERED"
    lines[0] = json.dumps(rec, sort_keys=True)
    led.path.write_text("\n".join(lines) + "\n")
    assert led.verify_chain() is False


def test_portable_custom_root(tmp_path):
    """#5: works on any node-local root; no KM-specific path required."""
    root = tmp_path / "some" / "node" / "ledger"
    led = ObligationLedger(root=root)
    led.open("portable")
    assert (root / "obligations.ndjson").exists()


def test_evidence_classifier():
    assert classify_evidence("done") == EvidenceTier.E0_CLAIM
    assert classify_evidence("~/x/proof.json") == EvidenceTier.E1_ARTIFACT
    assert classify_evidence("rcpt_abc123 at /a/b.py hash a1b2c3d4e5f60718") == EvidenceTier.E2_VERIFIED


def test_boundary_refuses_live_cylinder_dir(tmp_path):
    """#7 (HARD): the ledger refuses any root inside the live Tiger cylinder infra."""
    bad = tmp_path / "Tiger_1a" / "cylinders"
    with pytest.raises(LedgerBoundaryError):
        ObligationLedger(root=bad)
    # env-var route is guarded too
    os.environ["OBLIGATION_LEDGER_ROOT"] = str(bad)
    try:
        with pytest.raises(LedgerBoundaryError):
            ObligationLedger()
    finally:
        del os.environ["OBLIGATION_LEDGER_ROOT"]
