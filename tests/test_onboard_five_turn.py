# -*- coding: utf-8 -*-
"""Phase 1 ONBOARD (KM GO 2026-08-11) — the fresh-human 5-turn onboard: AI proposes, human disposes.

AA's GREEN conditions, proven here:
- OFFLINE COMPLETE       — turns 1–5 finish with no network / no cloud / no account (the flow imports no socket).
- NO SILENT WRITE        — nothing is written that is not traceable to a human turn; declining writes nothing.
- TURN-1 TEXT BEFORE MINT — the key-ceremony text is presented BEFORE any key exists on disk.
- HONESTY (four checks)  — (a) no key until the turn-1 accept; (b) the first gated act passes the sealed human
                            gate; (c) the receipt is signed by the human's OWN key and verifies WITHOUT the AI;
                            (d) UAT receipts carry uat:true, never use principal KM-1176, and never enter a seal
                            ledger (they land in a local onboard log only).
"""
import json
import pathlib

import pytest

from _substrate import substrate_available  # noqa: E402
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

from sovereign_agent.onboarding.onboard import (
    run_onboard, verify_onboard_receipt, OnboardOutcome, OnboardReceipt, OnboardError,
    KEY_CEREMONY_TEXT, DEFAULT_GATED_ACTS,
)
from sovereign_agent.keystore.node_keystore import has_node_key

AT = "2026-08-11T00:00:00Z"


def _scripted(dispositions, *, keystore_dir=None, node_id="node", seen=None):
    """A prompter that replays a fixed disposition per turn.kind and records the turns it saw (order proof).
    For the turn-1 accept it asserts NO key exists yet — proving the ceremony text is shown before any mint."""
    def prompter(turn):
        if seen is not None:
            seen.append((turn.n, turn.kind))
        if turn.kind == "accept" and keystore_dir is not None:
            assert not has_node_key(keystore_dir, node_id), "a key existed BEFORE the turn-1 accept"
            assert "no recovery service" in turn.text.lower() and "no passphrase" in turn.text.lower()
        return dispositions[turn.kind]
    return prompter


def test_decline_at_turn_1_writes_no_key(tmp_path):
    ks = str(tmp_path / "ks")
    seen = []
    out = run_onboard(ks, prompter=_scripted({"accept": False}, keystore_dir=ks, seen=seen), at=AT)
    assert isinstance(out, OnboardOutcome) and out.key_written is False and out.turn == 1
    assert has_node_key(ks, "node") is False                      # NO key written on decline
    assert not pathlib.Path(ks, "node.nodekey.json").exists()
    assert out.writes == ()                                        # no silent write of any kind
    assert seen == [(1, "accept")]                                # stopped at turn 1


def test_five_turns_in_order_and_every_write_traced(tmp_path):
    ks = str(tmp_path / "ks")
    seen = []
    disp = {"accept": True, "name": "Ada's Laptop", "edit_set": ["send_value"], "gate": "approved"}
    r = run_onboard(ks, prompter=_scripted(disp, keystore_dir=ks, seen=seen), at=AT, uat=True)
    assert isinstance(r, OnboardReceipt)
    # the five turns ran in the fixed order
    assert seen == [(1, "accept"), (2, "name"), (3, "edit_set"), (4, "gate")]
    # every write is traced to a human turn (mint→1, name→2, gated acts→3, gate→4, receipt→5)
    turns_that_wrote = sorted({w["turn"] for w in r.writes})
    assert turns_that_wrote == [1, 2, 3, 4, 5]
    assert any(w["write"].startswith("generate_node_key") and w["turn"] == 1 for w in r.writes)
    assert r.node_name == "Ada's Laptop" and r.gated_acts == ("send_value",)
    assert r.first_gate["status"] == "approved" and r.first_gate.get("real") is True   # sealed gate, real disposition


def test_receipt_verifies_offline_without_the_ai(tmp_path):
    ks = str(tmp_path / "ks")
    disp = {"accept": True, "name": "node-a", "edit_set": list(DEFAULT_GATED_ACTS), "gate": "deny"}
    r = run_onboard(ks, prompter=_scripted(disp, keystore_dir=ks), at=AT, uat=True)
    # the human (or AA/Dragon) verifies the receipt from the key alone — no AI in the loop
    assert verify_onboard_receipt(r, ks) is True
    assert r.first_gate["status"] == "denied"                     # the human's DENY is honoured
    # tamper the signed payload → verification fails
    bad = OnboardReceipt(**{**r.__dict__, "signature": ("0" * len(r.signature))})
    assert verify_onboard_receipt(bad, ks) is False


def test_uat_receipt_is_flagged_local_and_never_in_a_seal_ledger(tmp_path):
    ks = str(tmp_path / "ks")
    disp = {"accept": True, "name": "uat-operator", "edit_set": ["send_value"], "gate": "approved"}
    r = run_onboard(ks, prompter=_scripted(disp, keystore_dir=ks), at=AT, uat=True)
    assert r.uat is True and r.principal != "KM-1176"
    # the receipt landed in a LOCAL onboard log, never a seal ledger
    assert pathlib.Path(r.receipt_path).name == "onboard_receipts.ndjson"
    assert "seal_ledger" not in r.receipt_path
    row = json.loads(pathlib.Path(r.receipt_path).read_text().splitlines()[-1])
    assert row["uat"] is True and row["receipt_kind"] == "onboard"
    # a UAT onboard may never use the sovereign principal
    with pytest.raises(OnboardError):
        run_onboard(ks, prompter=_scripted({"accept": True, "name": "KM-1176",
                                            "edit_set": ["send_value"], "gate": "approved"},
                                           keystore_dir=ks, node_id="node2"), at=AT, uat=True, node_id="node2")


def test_onboard_flow_imports_no_network():
    # OFFLINE: the onboard module pulls in no socket/requests/urllib/http client — turns 1–5 need no cloud.
    # Check for real network CODE (imports/calls), not the descriptive prose ("no telemetry") in the docstring.
    import sovereign_agent.onboarding.onboard as m
    src = pathlib.Path(m.__file__).read_text()
    for net in ("import socket", "import requests", "import urllib", "urllib.request", "urllib.urlopen",
                "http.client", "httpx", "socket.socket", ".connect(", "requests.get", "requests.post"):
        assert net not in src, f"onboard flow must be offline — found network token {net!r}"
