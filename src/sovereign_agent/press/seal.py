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


def _canonical(rec):
    """Signed payload = the receipt minus its own signature fields, canonically ordered."""
    body = {k: v for k, v in rec.items() if k not in ("signature", "receipt_sha256")}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign(rec, key):
    return hmac.new(key, _canonical(rec), hashlib.sha256).hexdigest()


def load_chain(ledger_path):
    """Read through the ONE ndjson gateway (Universalize Wave §1) — never a raw per-line
    parse. A ledger truncated mid-append loads its clean prefix instead of raising, and a
    short prefix then fails chain verification loudly rather than silently."""
    if not os.path.exists(ledger_path):
        return []
    from ..ndjson import read_ndjson
    return list(read_ndjson(ledger_path).entries)


def make_receipt(volume, word, artifact_sha, edition, prior_hash, key, principal, now=None):
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
    rec["signature"] = sign(rec, key)
    rec["receipt_sha256"] = hashlib.sha256(_canonical(rec)).hexdigest()[:16]
    return rec


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


def latest_for(chain, volume):
    for rec in reversed(chain):
        if rec.get("volume") == volume:
            return rec
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
