"""The seal gate and the docs projection — proved by their REFUSALS, not their happy paths.

The property under test throughout: the Press cannot seal, a web session cannot seal, and a
projection cannot change anything. Each of those is a refusal, so each gets a test.
"""
import json
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sovereign_agent.press import publish as pubmod  # noqa: E402
from sovereign_agent.press import seal as sealmod  # noqa: E402

KEY = b"x" * 48
VOL = {"title": "The Test Volume", "series": "S9", "stage": "published",
       "freeze_sha": "a" * 64, "gates": ["gate one"]}


def _ledger(tmp_path, *recs):
    p = tmp_path / sealmod.SEAL_LEDGER
    with open(p, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return str(tmp_path)


def _chain(n=2):
    out, prior = [], None
    for i in range(n):
        rec = sealmod.make_receipt(f"V-{i}", "the word", "b" * 64, "published", prior, KEY,
                                   now="20260719T000000Z")
        out.append(rec)
        prior = rec["receipt_sha256"]
    return out


# ── the key is the gate ────────────────────────────────────────────────────────

def test_no_key_means_no_seal(monkeypatch):
    """Absent key = fail-closed. This is what makes 'the site cannot seal' structural:
    the site holds no key, so it cannot produce a receipt that verifies."""
    monkeypatch.delenv("PRESS_SEAL_KEY", raising=False)
    key, err = sealmod._key()
    assert key is None and "operator's key" in err


def test_weak_key_refused(tmp_path, monkeypatch):
    p = tmp_path / "k"
    p.write_bytes(b"short")
    monkeypatch.setenv("PRESS_SEAL_KEY", str(p))
    key, err = sealmod._key()
    assert key is None and "too short" in err


def test_receipt_signed_by_a_different_key_does_not_verify():
    """A forged receipt — right shape, wrong signer — is refused. Possession of the
    format is not possession of the gate."""
    forged = sealmod.make_receipt("V-0", "the word", "b" * 64, "published", None,
                                  b"y" * 48, now="20260719T000000Z")
    fails = sealmod.verify_chain([forged], KEY)
    assert any("signature invalid" in f for f in fails)


def test_tampered_receipt_content_breaks_the_signature():
    chain = _chain(1)
    chain[0]["artifact_sha256"] = "c" * 64   # swap the artifact after sealing
    fails = sealmod.verify_chain(chain, KEY)
    assert any("signature invalid" in f for f in fails)


def test_reordered_or_dropped_receipt_breaks_the_chain():
    chain = _chain(3)
    del chain[1]
    fails = sealmod.verify_chain(chain, KEY)
    assert any("chain break" in f for f in fails)


def test_intact_chain_verifies():
    assert sealmod.verify_chain(_chain(3), KEY) == []


def test_word_is_recorded_but_not_stored_plaintext():
    """A seal is traceable to a human utterance; the utterance itself is not left lying
    in the ledger."""
    rec = sealmod.make_receipt("V-0", "S0v7", "b" * 64, "published", None, KEY)
    assert "S0v7" not in json.dumps(rec)
    assert rec["word_sha256"] == __import__("hashlib").sha256(b"S0v7").hexdigest()


# ── is_sealed: unverifiable is NOT sealed ──────────────────────────────────────

def test_unverifiable_ledger_is_not_sealed(tmp_path):
    chain = _chain(2)
    chain[1]["signature"] = "0" * 64
    root = _ledger(tmp_path, *chain)
    ok, why = sealmod.is_sealed(root, "V-1", key=KEY)
    assert ok is False and "does not verify" in why


def test_missing_receipt_is_not_sealed(tmp_path):
    ok, why = sealmod.is_sealed(str(tmp_path), "V-0", key=KEY)
    assert ok is False and "no seal receipt" in why


# ── the projection refuses to leak ─────────────────────────────────────────────

def test_public_surface_refuses_unsealed(tmp_path):
    """The operator's ruling: public docs carry SEALED only. Provisional stays private."""
    written, refused = pubmod.publish({"V-1": VOL}, "V-1", str(tmp_path),
                                      str(tmp_path / "out"), surface="public", key=KEY)
    assert written == []
    assert refused and "SEALED only" in refused[0][1]


def test_internal_surface_publishes_unsealed_with_the_command_not_a_button(tmp_path):
    written, refused = pubmod.publish({"V-1": VOL}, "V-1", str(tmp_path),
                                      str(tmp_path / "out"), surface="internal", key=KEY)
    assert refused == [] and len(written) == 1
    card = open(written[0][1], encoding="utf-8").read()
    assert "press seal V-1" in card          # renders the command
    assert "this page cannot perform it" in card


def test_public_surface_publishes_a_sealed_volume_with_its_receipt(tmp_path):
    rec = sealmod.make_receipt("V-1", "the word", VOL["freeze_sha"], "published", None, KEY)
    root = _ledger(tmp_path, rec)
    written, refused = pubmod.publish({"V-1": VOL}, "V-1", root, str(tmp_path / "out"),
                                      surface="public", key=KEY)
    assert refused == [] and len(written) == 1
    card = open(written[0][1], encoding="utf-8").read()
    assert rec["receipt_sha256"] in card
    assert "Sealed" in card


def test_card_carries_the_grade(tmp_path):
    """A spec that loses its grade in projection is a spec that lies politely."""
    prov = dict(VOL, stage="built-in-review")
    written, _ = pubmod.publish({"V-2": prov}, "V-2", str(tmp_path), str(tmp_path / "out"),
                                surface="internal", key=KEY)
    card = open(written[0][1], encoding="utf-8").read()
    assert "Provisional" in card and "designed · building" in card


def test_dry_run_writes_nothing(tmp_path):
    out = tmp_path / "out"
    written, _ = pubmod.publish({"V-1": VOL}, "V-1", str(tmp_path), str(out),
                                surface="internal", key=KEY, dry_run=True)
    assert written and not out.exists()


def test_unknown_volume_is_default_deny(tmp_path):
    written, refused = pubmod.publish({"V-1": VOL}, "NOPE", str(tmp_path),
                                      str(tmp_path / "out"), surface="internal", key=KEY)
    assert written == [] and "default-deny" in refused[0][1]


def test_card_stays_concise(tmp_path):
    """The operator asked for concise, not verbose — a screen per volume."""
    written, _ = pubmod.publish({"V-1": VOL}, "V-1", str(tmp_path), str(tmp_path / "out"),
                                surface="internal", key=KEY)
    assert written[0][2] < 200, "spec card grew past a screen"


def test_bad_surface_refused():
    with pytest.raises(ValueError):
        pubmod.publish({}, "--all", ".", ".", surface="everywhere")
