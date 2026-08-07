# -*- coding: utf-8 -*-
"""CR-2 dual-sign acceptance tests (KM cutover-conditional, 2026-08-07).

Proves: dual-sign is OFF by default (the press seals on current HMAC-only law) · when enabled with an
operator ECDSA key, a NEW receipt carries a sealed-P1 ECDSA signature ALONGSIDE the HMAC over the SAME
canonical body · HMAC-only history verifies UNCHANGED · a dual-signed link verifies PUBLIC-ONLY (no
secret) · tamper and a foreign key are rejected · the HMAC signature and receipt_sha256 are identical
whether or not the ECDSA fields are present (history is never touched).
"""
import hashlib
import pytest

from sovereign_agent.press import seal as S
from sovereign_agent._lazy_bp import secp256k1_curve

_HMAC_KEY = b"x" * 48


def _priv_hex():
    c = secp256k1_curve() if callable(secp256k1_curve) else secp256k1_curve
    return f"{(0x00c0ffee1234567890abcdefabcdef1234567890abcdefabcdef1234567890ab % c.n):064x}"


def _mk(monkeypatch, dual, prior=None):
    if dual:
        monkeypatch.setenv("PRESS_DUAL_SIGN", "1")
        monkeypatch.setenv("PRESS_ECDSA_KEY", _priv_hex())
    else:
        monkeypatch.delenv("PRESS_DUAL_SIGN", raising=False)
    return S.make_receipt("s8_test", "the word", "artifactsha", "e1", prior, _HMAC_KEY, "KM-1176")


# ---- OFF by default: the press seals on current law -------------------------------------------

def test_dual_sign_off_by_default(monkeypatch):
    monkeypatch.delenv("PRESS_DUAL_SIGN", raising=False)
    rec = _mk(monkeypatch, dual=False)
    assert "ecdsa_signature" not in rec and "sig_scheme" not in rec
    assert rec["signature"] and rec["receipt_sha256"]  # HMAC seal stands alone


def test_enabled_but_no_key_is_refused_loudly(monkeypatch):
    # FAIL-LOUD (KM ruling 2026-08-07): the graceful HMAC-only fallback is retired — PRESS_DUAL_SIGN
    # set with no operator key REFUSES the seal with a named reason rather than sealing weaker.
    monkeypatch.setenv("PRESS_DUAL_SIGN", "1")
    monkeypatch.delenv("PRESS_ECDSA_KEY", raising=False)
    monkeypatch.delenv("PRESS_ECDSA_KEY_FILE", raising=False)
    with pytest.raises(S.SealRefused) as ei:
        S.make_receipt("s8_test", "w", "a", "e1", None, _HMAC_KEY, "KM-1176")
    assert "SEAL REFUSED" in str(ei.value) and "PRESS_ECDSA_KEY" in str(ei.value)


def test_sig_scheme_reported_hmac_only_when_off(monkeypatch):
    # the console prints sig_scheme on EVERY seal; an HMAC-only receipt reports 'hmac-only'
    monkeypatch.delenv("PRESS_DUAL_SIGN", raising=False)
    rec = S.make_receipt("s8_test", "w", "a", "e1", None, _HMAC_KEY, "KM-1176")
    assert "sig_scheme" not in rec  # history parity: HMAC-only receipts carry no sig_scheme field
    assert S.receipt_sig_scheme(rec) == "hmac-only"  # but the console reports it


def test_sig_scheme_reported_dual_when_on(monkeypatch):
    rec = _mk(monkeypatch, dual=True)
    assert S.receipt_sig_scheme(rec) == "hmac+ecdsa-secp256k1"


def test_malformed_key_refused_by_name_not_traceback(monkeypatch):
    # B-11 (KM 2026-08-07): a PRESENT-but-unusable key is a named SealRefused, never a raw ValueError.
    monkeypatch.setenv("PRESS_DUAL_SIGN", "1")
    for bad in ("not-hex-zzzz", "   ", "\n\t "):
        monkeypatch.setenv("PRESS_ECDSA_KEY", bad)
        with pytest.raises(S.SealRefused):
            S.make_receipt("s8_test", "w", "a", "e1", None, _HMAC_KEY, "KM-1176")


def test_malformed_key_file_refused_by_name(monkeypatch, tmp_path):
    monkeypatch.setenv("PRESS_DUAL_SIGN", "1")
    monkeypatch.delenv("PRESS_ECDSA_KEY", raising=False)
    kf = tmp_path / "ecdsa_key"; kf.write_text("   \n")  # whitespace-only key file
    monkeypatch.setenv("PRESS_ECDSA_KEY_FILE", str(kf))
    with pytest.raises(S.SealRefused):
        S.make_receipt("s8_test", "w", "a", "e1", None, _HMAC_KEY, "KM-1176")


# ---- ON: a new receipt is dual-signed, HMAC + receipt_sha256 UNCHANGED ------------------------

def test_dual_signed_receipt_carries_ecdsa(monkeypatch):
    rec = _mk(monkeypatch, dual=True)
    assert rec["sig_scheme"] == "hmac+ecdsa-secp256k1"
    assert len(rec["ecdsa_pubkey"]) == 128 and len(rec["ecdsa_signature"]) == 128


def test_hmac_and_id_unchanged_by_dual_sign(monkeypatch):
    off = _mk(monkeypatch, dual=False)
    on = _mk(monkeypatch, dual=True)
    # identical inputs → identical HMAC signature and receipt id whether or not ECDSA is added
    assert on["signature"] == off["signature"]
    assert on["receipt_sha256"] == off["receipt_sha256"]


# ---- verification: HMAC unchanged, ECDSA public-only -----------------------------------------

def test_hmac_chain_verifies_with_or_without_ecdsa(monkeypatch):
    r1 = _mk(monkeypatch, dual=False, prior=None)
    r2 = S.make_receipt("s8_two", "w2", "a2", "e1", r1["receipt_sha256"], _HMAC_KEY, "KM-1176")  # dual (env still on? reset)
    monkeypatch.setenv("PRESS_DUAL_SIGN", "1"); monkeypatch.setenv("PRESS_ECDSA_KEY", _priv_hex())
    r2 = S.make_receipt("s8_two", "w2", "a2", "e1", r1["receipt_sha256"], _HMAC_KEY, "KM-1176")
    assert S.verify_chain([r1, r2], _HMAC_KEY) == []  # mixed HMAC-only + dual-signed: HMAC verifies both


def test_public_only_verify_of_a_dual_signed_link(monkeypatch):
    rec = _mk(monkeypatch, dual=True)
    res = S.verify_public([rec])
    assert res["failures"] == [] and res["public_verified"] == 1


def test_public_verify_flags_tampered_dual_signed_receipt(monkeypatch):
    rec = _mk(monkeypatch, dual=True)
    rec["artifact_sha256"] = "tampered"  # alter the signed body after sealing
    res = S.verify_public([rec])
    assert res["public_verified"] == 0 and res["failures"]


def test_public_verify_flags_foreign_key(monkeypatch):
    rec = _mk(monkeypatch, dual=True)
    # swap in a foreign public key: the signature no longer verifies against it
    c = secp256k1_curve() if callable(secp256k1_curve) else secp256k1_curve
    fp = c.mul((int(_priv_hex(), 16) + 1) % c.n)
    rec["ecdsa_pubkey"] = f"{fp[0]:064x}{fp[1]:064x}"
    res = S.verify_public([rec])
    assert res["public_verified"] == 0 and res["failures"]


def test_hmac_only_history_is_not_a_public_failure(monkeypatch):
    r1 = _mk(monkeypatch, dual=False, prior=None)  # pre-cutover, HMAC-only
    res = S.verify_public([r1])
    assert res["failures"] == [] and res["hmac_only"] == 1 and res["public_verified"] == 0
