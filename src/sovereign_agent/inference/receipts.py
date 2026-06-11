"""
Inference Receipts — the constitutional anchor (co-extrusion of *Sovereign Inference & Memory* Ch 3).

Every inference event produces a 9-field receipt; the receipt IS the constitutional act, hash-bound and
chained. This is the trust-layer foundation Vol 1 Ch 3 teaches, in code: the same nine structural fields,
the same chain reference (prior-cylinder hash), the same audit-chainability guarantee.

Book ↔ code anchor (Tech/Arch 17.6):
  Ch 3 "What a Receipt Contains" (9 fields)         → REQUIRED_FIELDS + build_receipt()
  Ch 3 "The P1 Signature / unmodified since signing" → receipt_hash() over canonical JSON (P5 Merkle-friendly)
  Ch 3 "The Chain — audit-chainability across periods" → chain_reference + verify_chain()

SOURCE/TRUTH/INTEGRITY: the operator_identity flows end-to-end (no hardcoded principal); references resolve;
state changes are append-only + hash-verified (a tampered field breaks the chain, loudly).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

# The nine structural fields (Ch 3). A receipt is invalid without all nine.
REQUIRED_FIELDS = (
    "model_identity", "input_hash", "output_hash", "sensitivity_class", "routing_decision",
    "operator_identity", "timestamp", "constitutional_reference", "chain_reference",
)


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def content_hash(content: str) -> str:
    """SHA-256 of content — makes input/output audit-chainable WITHOUT leaking the content (Ch 3 field 2/3)."""
    return _sha256(content or "")


def receipt_hash(receipt: dict) -> str:
    """Hash over the receipt's nine fields — the P5 Merkle-friendly anchor proving the receipt is unmodified
    since signing (Ch 3). The chain_reference's own receipt_hash is EXCLUDED (it cannot hash itself)."""
    core = {k: receipt[k] for k in REQUIRED_FIELDS if k in receipt}
    cr = dict(core.get("chain_reference") or {})
    cr.pop("receipt_hash", None)
    core["chain_reference"] = cr
    return _sha256(json.dumps(core, sort_keys=True))


def build_receipt(*, model_identity: str, input_content: str, output_content: str,
                  sensitivity_class: str, routing_decision: dict, operator_identity: str,
                  constitutional_reference: dict, prior_hash: str = "genesis",
                  timestamp: Optional[str] = None) -> dict:
    """Assemble a 9-field inference receipt (Ch 3 worked example). operator_identity flows in from the
    caller (SOURCE — no hardcoded principal); the chain_reference binds it to the prior cylinder."""
    r = {
        "model_identity": model_identity,
        "input_hash": content_hash(input_content),
        "output_hash": content_hash(output_content),
        "sensitivity_class": sensitivity_class,
        "routing_decision": routing_decision,
        "operator_identity": operator_identity,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "constitutional_reference": constitutional_reference,
        "chain_reference": {"prior_cylinder": prior_hash},
    }
    r["chain_reference"]["receipt_hash"] = receipt_hash(r)  # this receipt's own anchor
    return r


def validate_receipt(receipt: dict) -> tuple[bool, list[str]]:
    """A receipt is valid iff all nine fields are present (Ch 3: 'invalid without all nine') AND its stored
    receipt_hash recomputes (unmodified-since-signing). Returns (ok, reasons) — loud, not silent (§4)."""
    missing = [f for f in REQUIRED_FIELDS if f not in receipt or receipt[f] in (None, "")]
    if missing:
        return False, [f"missing required field(s): {', '.join(missing)}"]
    stored = (receipt.get("chain_reference") or {}).get("receipt_hash")
    if stored and stored != receipt_hash(receipt):
        return False, ["receipt_hash does not recompute — receipt modified after signing"]
    return True, []


def verify_chain(receipts: list[dict]) -> bool:
    """True iff every receipt links to its predecessor (chain_reference.prior_cylinder == prior.receipt_hash)
    and each receipt validates. The audit chain's immutability + independent verifiability (Ch 3)."""
    prev = "genesis"
    for r in receipts:
        ok, _ = validate_receipt(r)
        if not ok:
            return False
        if (r.get("chain_reference") or {}).get("prior_cylinder") != prev:
            return False
        prev = (r.get("chain_reference") or {}).get("receipt_hash")
    return True
