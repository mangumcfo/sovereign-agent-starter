"""ObligationLedger — node-local B32 obligation ledger (R-23 Phase 1).

A dr/cr, append-only, hash-chained, evidence-tiered obligation ledger that lives INSIDE the
sovereign node, on its OWN storage root. It vendors the patterns from the live B32 primitives
(see __init__ provenance) but is fully self-contained — it never imports or mutates the live
Tiger cylinder chain.

Lifecycle:
    open(...)   -> a DRAFT action-proposal (debit)  [CYL-006: all actions start draft]
    approve(id) -> flips draft->approved (the approval gate; Phase 2 wires this to the node breath-gate)
    close(id, evidence) -> credit: evidence is tier-classified, a receipt is minted, the obligation closes
Everything is appended to a single NDJSON chain (prev_hash linked); state is reconstructed by replay().
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# ── evidence tiers (vendored from breath_32 v2.1 + task_chain.py) ──────────
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


# ── hard boundary: never touch the live seal chain ────────────────────────
class LedgerBoundaryError(RuntimeError):
    """Raised if the ledger root would land inside the protected live cylinder infra."""


# Substrings that must never appear in a resolved ledger root (the live Tiger seal chain).
FORBIDDEN_ROOT_FRAGMENTS = (os.path.join("Tiger_1a", "cylinders"),)

ENV_ROOT = "OBLIGATION_LEDGER_ROOT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(obj: dict) -> str:
    """SHA-256 of canonical JSON, first 16 hex (matches the cylinder/molt convention)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def _entry_id() -> str:
    return f"obl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"


def _receipt_id() -> str:
    return f"rcpt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"


def _default_root() -> Path:
    # ledger.py -> obligations -> sovereign_agent -> src -> <repo root>
    repo = Path(__file__).resolve().parents[3]
    return repo / "memory" / "obligations"


def _resolve_root(root: Optional[os.PathLike | str]) -> Path:
    if root is None:
        root = os.environ.get(ENV_ROOT)
    p = Path(root).expanduser().resolve() if root else _default_root().resolve()
    s = str(p)
    for frag in FORBIDDEN_ROOT_FRAGMENTS:
        if frag in s:
            raise LedgerBoundaryError(
                f"ObligationLedger refuses root '{s}': it is inside the protected live "
                f"cylinder infra ('{frag}'). The node must never write the live seal chain. "
                f"Set {ENV_ROOT} to a node-local path."
            )
    return p


class ObligationLedger:
    """Append-only, hash-chained dr/cr obligation ledger on a node-local root."""

    def __init__(self, root: Optional[os.PathLike | str] = None,
                 principal_id: str = "node"):
        self.root = _resolve_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "obligations.ndjson"
        self.principal_id = principal_id

    # ── chain primitives ──────────────────────────────────────────────
    def _entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def _append(self, entry: dict) -> dict:
        entries = self._entries()
        entry["prev_hash"] = entries[-1]["hash"] if entries else "genesis"
        entry["hash"] = _hash({k: v for k, v in entry.items() if k != "hash"})
        with self.path.open("a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    # ── lifecycle ─────────────────────────────────────────────────────
    def open(self, title: str, owner: Optional[str] = None,
             classification: str = "C2", intent: Optional[str] = None,
             ref: Optional[str] = None) -> dict:
        """Open an obligation = a DRAFT action-proposal (debit). CYL-006: starts draft."""
        entry = {
            "type": "debit",
            "id": _entry_id(),
            "title": title,
            "owner": owner or self.principal_id,
            "principal_id": self.principal_id,
            "classification": classification,
            "intent": intent,
            "ref": ref,
            "draft": True,            # CYL-006
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "timestamp": _now(),
        }
        return self._append(entry)

    def approve(self, obligation_id: str, approved_by: str) -> dict:
        """Approve a draft (the approval gate). Phase 2 routes this through the node breath-gate."""
        entry = {
            "type": "approval",
            "id": _entry_id(),
            "approves": obligation_id,
            "approved_by": approved_by,
            "principal_id": self.principal_id,
            "timestamp": _now(),
        }
        return self._append(entry)

    def close(self, obligation_id: str, evidence: str,
              evidence_tier: Optional[str] = None, require_e1: bool = True,
              closed_by: Optional[str] = None) -> dict:
        """Close an obligation = credit, with evidence + a minted receipt.

        Rejects E0 (claim-only) when require_e1 is True (the default for material obligations).
        """
        tier = EvidenceTier(evidence_tier) if evidence_tier else classify_evidence(evidence)
        if require_e1 and tier == EvidenceTier.E0_CLAIM:
            raise ValueError(
                f"Evidence tier E0 (claim-only) insufficient to close '{obligation_id}'. "
                f"Provide an artifact pointer / hash / receipt (E1+)."
            )
        receipt = {
            "receipt_id": _receipt_id(),
            "obligation_id": obligation_id,
            "action": "close",
            "evidence": evidence,
            "evidence_tier": tier.value,
            "payload_hash": _hash({"obligation_id": obligation_id, "evidence": evidence}),
            "principal_id": closed_by or self.principal_id,
            "timestamp": _now(),
        }
        entry = {
            "type": "credit",
            "id": _entry_id(),
            "closes": obligation_id,
            "evidence": evidence,
            "evidence_tier": tier.value,
            "closed_by": closed_by or self.principal_id,
            "principal_id": self.principal_id,
            "receipt": receipt,
            "timestamp": _now(),
        }
        return self._append(entry)

    # ── replay + materialized views ───────────────────────────────────
    def replay(self) -> dict:
        """Reconstruct state from the append-only chain."""
        entries = self._entries()
        debits = {e["id"]: e for e in entries if e.get("type") == "debit"}
        closed = {e["closes"] for e in entries if e.get("type") == "credit"}
        approved = {e["approves"] for e in entries if e.get("type") == "approval"}
        for oid in approved:
            if oid in debits:
                debits[oid] = {**debits[oid], "draft": False, "approved": True}
        open_obs = [d for oid, d in debits.items() if oid not in closed]
        closed_obs = [d for oid, d in debits.items() if oid in closed]
        return {"open": open_obs, "closed": closed_obs, "all": list(debits.values())}

    def open_obligations(self, owner: Optional[str] = None) -> list[dict]:
        obs = self.replay()["open"]
        return [o for o in obs if o["owner"] == owner] if owner else obs

    def by_status(self) -> dict:
        st = self.replay()
        return {"open": len(st["open"]), "closed": len(st["closed"]), "total": len(st["all"])}

    def by_owner(self) -> dict:
        out: dict[str, dict] = {}
        for o in self.replay()["all"]:
            d = out.setdefault(o["owner"], {"open": 0, "closed": 0})
            d["open"] += 1
        closed_ids = {e["closes"] for e in self._entries() if e.get("type") == "credit"}
        for o in self.replay()["all"]:
            if o["id"] in closed_ids:
                out[o["owner"]]["open"] -= 1
                out[o["owner"]]["closed"] += 1
        return out

    def verify_chain(self) -> bool:
        """Recompute the hash chain; True iff every prev_hash + hash is intact."""
        prev = "genesis"
        for e in self._entries():
            if e.get("prev_hash") != prev:
                return False
            if e.get("hash") != _hash({k: v for k, v in e.items() if k != "hash"}):
                return False
            prev = e["hash"]
        return True
