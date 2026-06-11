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

import fcntl
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


class AlreadyClosedError(RuntimeError):
    """Raised by close() when an obligation has already been credited/closed (audit guard)."""


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
                 principal_id: str = "node",
                 gate=None, attestor=None):
        """gate / attestor are OPTIONAL duck-typed callables (thin-waist injection):
          gate(action: str, obligation: dict) -> {"status": "approved"|"denied", ...}
              — the node's breath-gate / human-approval disposition (Phase 2).
          attestor(action_class: str, principal_id: str, payload: dict, result_summary: str)
              -> {"receipt_hash": str, ...}   — mints a real node receipt/attestation.
        Both default None → fully standalone (Phase-1 behavior; tests stay green).
        `node_integration.wire_node_ledger` adapts the node's real HumanApprovalGate +
        ComplianceEngine into these contracts.
        """
        self.root = _resolve_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "obligations.ndjson"
        self.principal_id = principal_id
        self.gate = gate
        self.attestor = attestor

    # ── chain primitives ──────────────────────────────────────────────
    def _entries(self) -> list[dict]:
        # Parse-cache keyed by (st_mtime_ns, st_size) (audit perf fix): GET /obligations triggered
        # 6 full NDJSON parses per request (replay/by_status/by_owner/verify_chain). Re-reads only when
        # the file actually changes — so a multi-instance/append-by-another-process is still caught.
        if not self.path.exists():
            self._entries_cache = ([], None)
            return []
        st = self.path.stat()
        key = (st.st_mtime_ns, st.st_size)
        cache = getattr(self, "_entries_cache", None)
        if cache is not None and cache[1] == key:
            return cache[0]
        out = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        self._entries_cache = (out, key)
        return out

    def _is_closed(self, obligation_id: str) -> bool:
        return any(e.get("type") == "credit" and e.get("closes") == obligation_id
                   for e in self._entries())

    def _stat_key(self) -> tuple:
        """Identity of the on-disk chain: (mtime_ns, size). This is the SAME trust key `_entries()`
        uses for its parse cache — so memoizing verify_chain on it is no weaker than the parse cache
        already is. A genuine append/edit bumps the key; an unchanged file is treated as unchanged."""
        if not self.path.exists():
            return ("genesis", 0)
        st = self.path.stat()
        return (st.st_mtime_ns, st.st_size)

    def _append(self, entry: dict) -> dict:
        # CRITICAL write-fence (audit 2026-06-10): an exclusive flock over the read-tail-THROUGH-write
        # critical section. Without it two appenders read the same tail, compute the same prev_hash, and
        # permanently fork the hash chain (verify_chain() False forever). O_APPEND alone is insufficient —
        # prev_hash needs the tail read INSIDE the lock. Every writer (in-process threads via threaded=True
        # AND cross-process scripts on the shared atrium_review root) funnels through here, so this one lock
        # closes both races. The sidecar .lock is advisory + never part of the chain.
        lock_path = self.root / "obligations.lock"
        with open(lock_path, "a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                # Was the chain VERIFIED-VALID immediately before this append? (cache key must match the
                # current pre-append file identity — any out-of-band change since the last verify bumps
                # the key, so we fall back to a full re-verify and still catch the tamper.)
                pre_cache = getattr(self, "_verify_cache", None)
                pre_valid = bool(pre_cache and pre_cache[0] == self._stat_key() and pre_cache[1])
                entries = self._entries()
                entry["prev_hash"] = entries[-1]["hash"] if entries else "genesis"
                entry["hash"] = _hash({k: v for k, v in entry.items() if k != "hash"})
                with self.path.open("a") as f:
                    f.write(json.dumps(entry, sort_keys=True) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                # Incremental verify frontier (scaling_receipted_engine): a correctly-linked entry appended
                # onto a known-valid chain leaves it valid — so advance the cached verdict to the new file
                # identity WITHOUT a full re-hash. If the pre-state wasn't known-valid, drop the cache so the
                # next verify_chain() recomputes from genesis.
                self._verify_cache = (self._stat_key(), True) if pre_valid else None
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return entry

    def repair_chain(self) -> dict:
        """Re-link an already-forked chain (audit chain-repair command). Reads every entry in file order,
        recomputes prev_hash + hash so the chain is internally valid again, and rewrites the ndjson — backing
        up the original to obligations.ndjson.forked.<n> first. Held under the same write-fence. The repaired
        chain re-hashes content (the fork already broke cryptographic continuity); the backup preserves the
        raw forked record for audit. Returns {repaired, was_valid, entries, backup}."""
        lock_path = self.root / "obligations.lock"
        with open(lock_path, "a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                if self.verify_chain():
                    return {"repaired": False, "was_valid": True, "entries": len(self._entries()), "backup": None}
                entries = self._entries()
                n = 0
                while (self.root / f"obligations.ndjson.forked.{n}").exists():
                    n += 1
                backup = self.root / f"obligations.ndjson.forked.{n}"
                backup.write_text(self.path.read_text())
                prev = "genesis"
                for e in entries:
                    e.pop("hash", None)
                    e["prev_hash"] = prev
                    e["hash"] = _hash({k: v for k, v in e.items() if k != "hash"})
                    prev = e["hash"]
                tmp = self.path.with_suffix(".ndjson.repair")
                tmp.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in entries))
                tmp.replace(self.path)
                return {"repaired": True, "was_valid": False, "entries": len(entries), "backup": str(backup)}
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    # ── lifecycle ─────────────────────────────────────────────────────
    def open(self, title: str, owner: Optional[str] = None,
             classification: str = "C2", intent: Optional[str] = None,
             ref: Optional[str] = None, material: bool = False,
             lgp: Optional[dict] = None, next_gate: Optional[str] = None) -> dict:
        """Open an obligation = a DRAFT action-proposal (debit). CYL-006: starts draft.

        material=True ⇒ a gated ledger requires human approval (breath-gate) before close.
        lgp (P0-2) ⇒ optional families-first contribution that travels WITH the obligation, e.g.
          {"alignment_score": "0.92", "families_first_impact": "+18% effective purchasing power (C2F)"}.
        next_gate ⇒ human-readable next human-disposition point (mirrors series_roadmap.yaml).
        """
        entry = {
            "type": "debit",
            "id": _entry_id(),
            "title": title,
            "owner": owner or self.principal_id,
            "principal_id": self.principal_id,
            "classification": classification,
            "intent": intent,
            "ref": ref,
            "material": bool(material),
            "draft": True,            # CYL-006
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "timestamp": _now(),
        }
        if lgp:
            entry["lgp"] = lgp          # P0-2: LGP travels with the obligation
        if next_gate:
            entry["next_gate"] = next_gate
        return self._append(entry)

    # ── lookups ───────────────────────────────────────────────────────
    def _get(self, obligation_id: str) -> Optional[dict]:
        for e in self._entries():
            if e.get("type") == "debit" and e.get("id") == obligation_id:
                return e
        return None

    def _is_approved(self, obligation_id: str) -> bool:
        return any(e.get("type") == "approval" and e.get("approves") == obligation_id
                   and e.get("disposition", "approved") == "approved"
                   for e in self._entries())

    def approve(self, obligation_id: str, approved_by: str,
                rationale: str = "") -> dict:
        """Approve a draft via the breath-gate. If a `gate` is injected, the disposition
        is the gate's verdict (human primacy); a DENY raises and is recorded."""
        if self._get(obligation_id) is None:  # audit guard: no orphan approvals
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        if self._is_closed(obligation_id):
            raise AlreadyClosedError(f"obligation '{obligation_id}' is already closed — cannot approve")
        disposition, gate_meta = "approved", None
        if self.gate is not None:
            verdict = self.gate("approve", {"id": obligation_id, "approved_by": approved_by,
                                            "rationale": rationale}) or {}
            disposition = verdict.get("status", "approved")
            gate_meta = verdict
        entry = {
            "type": "approval",
            "id": _entry_id(),
            "approves": obligation_id,
            "approved_by": approved_by,
            "disposition": disposition,
            "gate": gate_meta,
            "principal_id": self.principal_id,
            "timestamp": _now(),
        }
        self._append(entry)
        if disposition != "approved":
            raise PermissionError(
                f"Breath-gate DENIED approval of '{obligation_id}' (recorded). "
                f"Obligation stays open."
            )
        return entry

    def close(self, obligation_id: str, evidence: str,
              evidence_tier: Optional[str] = None, require_e1: bool = True,
              closed_by: Optional[str] = None) -> dict:
        """Close an obligation = credit, with evidence + a minted receipt.

        Rejects E0 (claim-only) when require_e1 is True (the default for material obligations).
        """
        ob = self._get(obligation_id)  # existence/closed guards FIRST — 'not found' beats 'bad evidence' (audit)
        if ob is None:
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        if self._is_closed(obligation_id):
            raise AlreadyClosedError(f"obligation '{obligation_id}' is already closed")
        tier = EvidenceTier(evidence_tier) if evidence_tier else classify_evidence(evidence)
        if require_e1 and tier == EvidenceTier.E0_CLAIM:
            raise ValueError(
                f"Evidence tier E0 (claim-only) insufficient to close '{obligation_id}'. "
                f"Provide an artifact pointer / hash / receipt (E1+)."
            )
        # Human primacy (CYL-006): a MATERIAL obligation cannot close until it has cleared
        # the breath-gate. Only enforced when a gate is wired (standalone stays unchanged).
        if self.gate is not None and ob and ob.get("material") and not self._is_approved(obligation_id):
            raise PermissionError(
                f"'{obligation_id}' is material and has not cleared the breath-gate; "
                f"call approve() (human disposition) before close."
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
        # Mint a real NODE receipt (USN Merkle attestation / SOX-style chain-of-custody) when a
        # node attestor is wired — the close then carries a node-attested, E2-grade receipt.
        if self.attestor is not None:
            node_receipt = self.attestor(
                "obligation_close", closed_by or self.principal_id,
                {"obligation_id": obligation_id, "evidence": evidence},
                f"closed obligation {obligation_id} (tier {tier.value})",
            ) or {}
            receipt["node_receipt"] = node_receipt
            receipt["node_receipt_hash"] = node_receipt.get("receipt_hash")
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
        # Only approvals actually DISPOSITIONED 'approved' count (audit fix): a denied/pending
        # approval entry must not flip a draft to approved in the replay view. Mirrors _is_approved.
        approved = {e["approves"] for e in entries
                    if e.get("type") == "approval" and e.get("disposition", "approved") == "approved"}
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

    def full_log(self) -> list[dict]:
        """
        Per-obligation materialized record incl. approval + close evidence/receipt — for
        read-only drilldowns (the Atrium book↔code / review lens). Newest first.
        """
        entries = self._entries()
        obs = {e["id"]: dict(e) for e in entries if e.get("type") == "debit"}
        for e in entries:
            t = e.get("type")
            if t == "approval" and e.get("approves") in obs:
                d = obs[e["approves"]]
                d["disposition"] = e.get("disposition", "approved")
                d["approved"] = d["disposition"] == "approved"  # denied/pending must not read as approved (audit fix)
                d["draft"] = not d["approved"]
                d["approved_by"] = e.get("approved_by")
                d["approval_rationale"] = e.get("rationale")
            elif t == "credit" and e.get("closes") in obs:
                d = obs[e["closes"]]
                d["status"] = "closed"
                d["evidence"] = e.get("evidence")
                d["evidence_tier"] = e.get("evidence_tier")
                d["closed_by"] = e.get("closed_by")
                rcpt = e.get("receipt") or {}
                d["receipt_id"] = rcpt.get("receipt_id")
                d["node_receipt_hash"] = rcpt.get("node_receipt_hash")
        out = []
        for _oid, d in obs.items():
            d.setdefault("status", "approved" if d.get("approved") else "draft")
            out.append(d)
        out.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return out

    def verify_chain(self) -> bool:
        """True iff every prev_hash + hash is intact.

        INCREMENTAL (scaling_receipted_engine): memoized on the file identity key (_stat_key). The hot
        path — many `chain_ok` reads between writes (GET /obligations recomputes it per request) — returns
        the cached verdict in O(1) instead of re-hashing the whole chain each time. A change to the file
        (our own append, or any out-of-band edit) bumps the key and forces a full recompute, so tampering
        is still caught the moment the file differs. Our in-lock append advances the frontier directly (see
        _append), so append-then-verify is O(1) too. Soundness note: this trusts the same (mtime_ns, size)
        key the _entries() parse cache already trusts — it is no weaker than the existing read path."""
        key = self._stat_key()
        cache = getattr(self, "_verify_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        ok = self._recompute_chain()
        self._verify_cache = (key, ok)
        return ok

    def _recompute_chain(self) -> bool:
        """Full hash-walk from genesis — the O(n) ground truth behind the memoized verify_chain."""
        prev = "genesis"
        for e in self._entries():
            if e.get("prev_hash") != prev:
                return False
            if e.get("hash") != _hash({k: v for k, v in e.items() if k != "hash"}):
                return False
            prev = e["hash"]
        return True

    def manifest(self) -> dict:
        """One-glance proof of ledger state (P0-1). Mirrors GB's gb_meta_cylinder ritual for the
        agent's OWN obligation chain: run after any open/approve/close and the last_hash changes +
        the obligation counts move — cryptographic + countable proof the agent's state updated.
        """
        entries = self._entries()
        last = entries[-1] if entries else None
        return {
            "file": str(self.path),
            "chain_entries": len(entries),
            "obligations": self.by_status(),
            "chain_valid": self.verify_chain(),
            "last_hash": last.get("hash") if last else None,
            "last_prev_hash": last.get("prev_hash") if last else None,
            "last_ts": last.get("timestamp") if last else None,
            "last_type": last.get("type") if last else None,
            "last_ref": (last.get("title") or last.get("closes") or last.get("approves") or "—") if last else None,
        }
