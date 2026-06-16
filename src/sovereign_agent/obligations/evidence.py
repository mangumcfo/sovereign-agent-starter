"""Evidence tiers (E0/E1/E2) + the classifier — extracted verbatim from ledger.py (audit 2026-06-16 #6).
Vendored from breath_32 v2.1 + task_chain.py. Re-exported by ledger.py for back-compat."""
from __future__ import annotations

import re
from enum import Enum


class EvidenceTier(str, Enum):
    E0_CLAIM = "E0"      # claim-only — insufficient to close a material obligation
    E1_ARTIFACT = "E1"   # artifact pointer (path / receipt / url / hash) — minimum to close
    E2_VERIFIED = "E2"   # artifact + verification (hash match / receipt chain) — preferred


def classify_evidence(evidence: str) -> EvidenceTier:
    """Classify an evidence string into E0/E1/E2 (regex heuristic, per breath_32 v2.1)."""
    s = evidence or ""
    has_hash = bool(re.search(r"[a-f0-9]{16,64}", s))
    has_path = bool(re.search(r"(/[\w/.\-]+|~[\w/.\-]+)", s))
    has_receipt = bool(re.search(r"(rcpt_[a-f0-9]+|receipt_id)", s))
    has_url = bool(re.search(r"https?://", s))
    has_msg = bool(re.search(r"(msg_|message_id)", s))
    if has_hash and (has_path or has_receipt):
        return EvidenceTier.E2_VERIFIED
    if has_path or has_receipt or has_url or has_msg or has_hash:
        return EvidenceTier.E1_ARTIFACT
    return EvidenceTier.E0_CLAIM
