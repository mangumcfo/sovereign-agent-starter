"""seal.py — the human seal gate as an instrument, not an automation.

The Press has never sealed and still does not. What this module adds is the OPERATOR'S
instrument for producing a seal that the ledger can verify: `press seal <volume> --word ...`.

Three properties make the gate structural rather than promised:

0. **A seal names its human.** `PRESS_PRINCIPAL` must be set; the kernel carries no
   identity of its own and refuses to invent one.
1. **A seal requires the operator's key.** Receipts are HMAC-signed with a key the operator
   holds (`PRESS_SEAL_KEY`, a file readable only by them). No key, no seal — the command
   refuses, loud and fail-closed. A web session, a build runner, or a remote node cannot
   produce a valid receipt because none of them hold the key. This is why a site "Seal"
   button renders the COMMAND rather than performing the seal: the site has nothing to sign
   with, by construction.
2. **A seal requires the operator's word.** `--word` carries the spoken seal word. It is
   recorded (hashed) in the receipt, so a seal is traceable to a specific human utterance,
   not merely to possession of a key.
3. **Seals are chained.** Each receipt carries the prior receipt's hash. Removing or
   reordering history breaks verification.

`press seal --verify` re-checks the whole chain from the ledger alone.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time

SEAL_LEDGER = "seal_ledger.jsonl"


def _key(env_get=os.environ.get, read=None):
    """The operator's signing key. Absent key = no sealing, ever (fail-closed)."""
    path = env_get("PRESS_SEAL_KEY")
    if not path:
        return None, ("PRESS_SEAL_KEY is not set — sealing requires the operator's key. "
                      "The Press cannot seal on anyone's behalf.")
    reader = read or (lambda p: open(p, "rb").read())
    try:
        material = reader(path)
    except OSError as e:
        return None, f"seal key unreadable at {path}: {e}"
    if len(material.strip()) < 32:
        return None, ("seal key is too short (<32 bytes) — refusing to sign a seal with a "
                      "weak key")
    return material.strip(), None


def principal(env_get=os.environ.get):
    """WHO sealed. The kernel carries no identity of its own and invents none: the
    operator names themselves via PRESS_PRINCIPAL, and an unnamed seal is refused.
    A receipt that cannot say who sealed it is not a seal."""
    who = (env_get("PRESS_PRINCIPAL") or "").strip()
    if not who:
        return None, ("PRESS_PRINCIPAL is not set — a seal must name the human who made "
                      "it. The kernel does not assume an identity.")
    return who, None


PLACEHOLDER = re.compile(r"^\s*$|^<.*>$|your word|placeholder|word here|change ?me|xxx+",
                         re.I)


def read_word(prompt, opener=None):
    """Take the seal word from the OPERATOR'S KEYBOARD, never from the command line.

    Field-earned. A word passed as an argument can be pasted from a document (and so can
    carry a placeholder), can be eaten out of a paste buffer by a shell `read`, and lands
    in shell history. Reading it here removes all three: the terminal is read directly, so
    a pasted command line cannot supply the word, and nothing about it survives in history.
    Placeholder-shaped words are refused outright — belt to the braces.

    /dev/tty is preferred because it is immune to whatever is queued on stdin. Where the
    console gives the shell no controlling terminal, we fall back to stdin — but only if
    stdin is a terminal, so `seal < words.txt` still cannot produce a seal.
    """
    import getpass
    import sys
    tty, via = None, None
    try:
        tty = (opener or open)("/dev/tty", "r+")
        via = "tty"
    except OSError:
        # Some consoles run the shell without a controlling terminal, so /dev/tty cannot be
        # opened (ENXIO) even though a human is plainly typing. Fall back to stdin ONLY when
        # stdin is itself a terminal — that keeps the property that matters (a script
        # redirecting stdin still cannot seal) while working where /dev/tty does not.
        if getattr(sys.stdin, "isatty", lambda: False)():
            via = "stdin"
        else:
            return None, ("no terminal available to read the seal word — a seal is spoken by "
                          "a human at a keyboard, not supplied by a script")
    try:
        word = getpass.getpass(prompt, stream=tty) if via == "tty" else getpass.getpass(prompt)
    finally:
        if tty is not None:
            tty.close()
    if PLACEHOLDER.match(word or ""):
        return None, (f"that is not a seal word ({word!r}) — it reads as a placeholder or "
                      "is empty; nothing was written")
    return word, None


# Fields excluded from the signed payload: the receipt's own signature/id fields AND the CR-2
# dual-sign fields (added AFTER the HMAC + receipt_sha256, so they change neither). Both the HMAC
# and the ECDSA sign this identical canonical body — the ECDSA is an independent second signature
# over the same payload, so HMAC-only history verifies exactly as before.
_UNSIGNED_FIELDS = ("signature", "receipt_sha256", "sig_scheme", "ecdsa_pubkey", "ecdsa_signature")


def _canonical(rec):
    """Signed payload = the receipt minus its own signature/id fields, canonically ordered."""
    body = {k: v for k, v in rec.items() if k not in _UNSIGNED_FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign(rec, key):
    return hmac.new(key, _canonical(rec), hashlib.sha256).hexdigest()


# ── CR-2 dual-sign (KM cutover-conditional, 2026-08-07): sealed-P1 ECDSA ALONGSIDE the HMAC chain.
#    Gated OFF by default — the press seals on current (HMAC-only) law until KM's cutover word sets
#    PRESS_DUAL_SIGN. History is never touched: old receipts carry no ecdsa fields and verify by HMAC
#    exactly as before; new receipts additionally carry a public-verifiable ECDSA signature over the
#    SAME canonical body. Verifying an ECDSA link needs only the public key (verify_public). ─────────
class SealRefused(Exception):
    """A seal was requested under conditions that would silently understate the record — refused
    loudly rather than sealed weaker than asked (KM ruling 2026-08-07: fail-loud, not fallback)."""


def _dual_sign_enabled(env_get=os.environ.get):
    """CR-2 first use ONLY on KM's cutover word — off by default; the press never waits on CR-2."""
    return str(env_get("PRESS_DUAL_SIGN", "")).strip().lower() in ("1", "true", "yes", "on")


def _ecdsa_key(env_get=os.environ.get, read=None):
    """The operator's persistent sealed-P1 (secp256k1) private key, as a hex scalar in PRESS_ECDSA_KEY
    (or a file at PRESS_ECDSA_KEY_FILE). Returns (private_int, public_hex) or (None, None) if absent —
    absence is not an error: dual-sign simply does not engage, and the HMAC seal stands alone."""
    hexkey = env_get("PRESS_ECDSA_KEY")
    if not hexkey:
        path = env_get("PRESS_ECDSA_KEY_FILE")
        rd = read or (lambda p: open(p).read())
        if path and os.path.exists(path):
            hexkey = rd(path)
    if not hexkey:
        return None, None
    priv = int(hexkey.strip(), 16)
    from .._lazy_bp import secp256k1_curve
    c = secp256k1_curve() if callable(secp256k1_curve) else secp256k1_curve
    priv %= c.n
    pub = c.mul(priv)  # persistent pubkey = priv·G
    return priv, f"{pub[0]:064x}{pub[1]:064x}"


def _ecdsa_sign(canonical_bytes, priv):
    """Sign the canonical receipt body with the sealed-P1 ECDSA, returning the signature as hex."""
    from .._lazy_bp import sign as _p1_sign
    return _p1_sign(priv, canonical_bytes).to_hex()


def _ecdsa_verify(canonical_bytes, sig_hex, pub_hex):
    """Verify an ECDSA receipt signature PUBLIC-ONLY — the public key alone, no secret. Returns bool."""
    try:
        from .._lazy_bp import verify as _p1_verify
        from breathline_primitives.layer1 import ECDSASignature  # sealed-P1 signature type
        pub = (int(pub_hex[:64], 16), int(pub_hex[64:128], 16))
        return bool(_p1_verify(pub, canonical_bytes, ECDSASignature.from_hex(sig_hex)))
    except Exception:
        return False


def load_chain(ledger_path):
    """Read through the ONE ndjson gateway (Universalize Wave §1) — never a raw per-line
    parse. A ledger truncated mid-append loads its clean prefix instead of raising, and a
    short prefix then fails chain verification loudly rather than silently."""
    if not os.path.exists(ledger_path):
        return []
    from ..ndjson import read_ndjson
    return list(read_ndjson(ledger_path).entries)


def superseded_ids(chain):
    """Receipt ids that a later receipt has superseded. Superseded receipts stay in the
    chain as history — they are never removed, only pointed past."""
    return {r["supersedes"] for r in chain if r.get("supersedes")}


def make_receipt(volume, word, artifact_sha, edition, prior_hash, key, principal,
                 now=None, supersedes=None):
    """The receipt both paths emit — identical by construction, because there is only
    one emitter. The site path renders the command that calls this; it never calls it."""
    rec = {
        "kind": "seal",
        "volume": volume,
        "edition": edition,
        "artifact_sha256": artifact_sha,
        "principal": principal,
        "word_sha256": hashlib.sha256(word.encode()).hexdigest(),
        "sealed_utc": now or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "prior_receipt_sha256": prior_hash,
        "law": ("sealing is a human act; this receipt proves the operator's key and word "
                "were both present. The Press never seals."),
    }
    if supersedes:
        rec["supersedes"] = supersedes
        rec["law"] += (" This receipt SUPERSEDES an earlier one, which remains in the chain "
                       "as history: the record is corrected by appending, never by rewriting.")
    rec["signature"] = sign(rec, key)
    rec["receipt_sha256"] = hashlib.sha256(_canonical(rec)).hexdigest()[:16]
    # CR-2 dual-sign: add a public-verifiable sealed-P1 ECDSA over the SAME canonical body, ONLY when
    # the cutover flag is set AND an operator ECDSA key is present. The fields are excluded from
    # _canonical, so neither the HMAC signature nor receipt_sha256 (already computed) changes.
    # FAIL-LOUD (KM ruling 2026-08-07): once the cutover flag is set, a MISSING operator key is a
    # REFUSAL, not a silent HMAC-only fallback — sealing weaker than the flag asked would understate
    # the record. (The graceful-fallback behavior is retired: PRESS_DUAL_SIGN set ⇒ a key is required.)
    if _dual_sign_enabled():
        priv, pub_hex = _ecdsa_key()
        if priv is None:
            raise SealRefused(
                "PRESS_DUAL_SIGN is set but no operator ECDSA key is present "
                "(PRESS_ECDSA_KEY or PRESS_ECDSA_KEY_FILE) — SEAL REFUSED. A dual-sign seal was "
                "requested; sealing HMAC-only under the dual-sign flag would silently understate the "
                "record. Provide the operator ECDSA key on the sealing iron, or unset PRESS_DUAL_SIGN "
                "to seal HMAC-only deliberately.")
        rec["sig_scheme"] = "hmac+ecdsa-secp256k1"
        rec["ecdsa_pubkey"] = pub_hex
        rec["ecdsa_signature"] = _ecdsa_sign(_canonical(rec), priv)
    return rec


def receipt_sig_scheme(rec):
    """The signature scheme of a receipt for console reporting — 'hmac+ecdsa-secp256k1' when a receipt
    carries a dual-signature, else 'hmac-only'. The console prints this on EVERY seal (KM ruling)."""
    return rec.get("sig_scheme", "hmac-only")


def verify_chain(chain, key):
    """Returns a list of failures; empty list = the chain verifies."""
    fails = []
    prior = None
    for i, rec in enumerate(chain):
        if rec.get("prior_receipt_sha256") != prior:
            fails.append(f"receipt {i} ({rec.get('volume')}): chain break — "
                         f"prior {rec.get('prior_receipt_sha256')!r}, expected {prior!r}")
        expect = sign(rec, key)
        if not hmac.compare_digest(rec.get("signature", ""), expect):
            fails.append(f"receipt {i} ({rec.get('volume')}): signature invalid — "
                         "content altered after sealing, or signed with a different key")
        prior = rec.get("receipt_sha256")
    return fails


def verify_public(chain):
    """PUBLIC-ONLY verification of the chain (CR-2) — no HMAC secret required.

    Verifies the prior-hash linkage for every receipt, and the sealed-P1 ECDSA signature for every
    receipt that carries one (`ecdsa_signature`), using only its embedded public key. Returns a dict:
      {failures: [...], public_verified: n, hmac_only: n}
    An HMAC-only (pre-cutover) receipt is NOT a failure — its linkage is checked and it is counted as
    `hmac_only` (publicly unverifiable by design; verify it with the key via verify_chain). A receipt
    that carries an ECDSA signature which does not verify against its own public key IS a failure.
    """
    failures, public_verified, hmac_only = [], 0, 0
    prior = None
    for i, rec in enumerate(chain):
        if rec.get("prior_receipt_sha256") != prior:
            failures.append(f"receipt {i} ({rec.get('volume')}): chain break — "
                            f"prior {rec.get('prior_receipt_sha256')!r}, expected {prior!r}")
        sig_hex, pub_hex = rec.get("ecdsa_signature"), rec.get("ecdsa_pubkey")
        if sig_hex and pub_hex:
            if _ecdsa_verify(_canonical(rec), sig_hex, pub_hex):
                public_verified += 1
            else:
                failures.append(f"receipt {i} ({rec.get('volume')}): ECDSA signature invalid — "
                                "content altered after sealing, or signed with a different key")
        else:
            hmac_only += 1
        prior = rec.get("receipt_sha256")
    return {"failures": failures, "public_verified": public_verified, "hmac_only": hmac_only}


def latest_for(chain, volume):
    """The ACTIVE receipt for a volume: the most recent one that nothing supersedes."""
    dead = superseded_ids(chain)
    for rec in reversed(chain):
        if rec.get("volume") == volume and rec.get("receipt_sha256") not in dead:
            return rec
    return None


def check_supersede(chain, volume, prior_id):
    """The rules a correction must satisfy. Returns an error string, or None."""
    match = [r for r in chain if r.get("receipt_sha256") == prior_id]
    if not match:
        return f"no receipt {prior_id!r} in the ledger — nothing to supersede"
    prior = match[0]
    if prior.get("volume") != volume:
        return (f"receipt {prior_id!r} seals {prior.get('volume')!r}, not {volume!r} — "
                "a correction stays within its own volume")
    if prior_id in superseded_ids(chain):
        return f"receipt {prior_id!r} is already superseded — corrections do not stack"
    return None


def is_sealed(runs_root, volume, key=None):
    """The single question `publish` and `release` ask. Unverifiable = NOT sealed."""
    chain = load_chain(os.path.join(runs_root, SEAL_LEDGER))
    rec = latest_for(chain, volume)
    if not rec:
        return False, "no seal receipt on file"
    if key is not None:
        if verify_chain(chain, key):
            return False, "seal ledger does not verify — refusing to treat as sealed"
    return True, rec
