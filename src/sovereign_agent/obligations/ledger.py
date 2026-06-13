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

# POSIX advisory lock for the write-fence. Guarded so the module imports on non-POSIX platforms
# (audit 2026-06-13: pyproject claims requires-python>=3.10 with no OS restriction, but a top-level
# `import fcntl` hard-failed on Windows at package load). On a platform without fcntl the fence degrades
# to a no-op with a ONE-TIME loud warning — never a silent weakening of the hash-chain fence.
try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover — non-POSIX
    _fcntl = None
    _HAS_FCNTL = False

_FLOCK_WARNED = False


def _flock_ex(fileobj) -> None:
    if _HAS_FCNTL:
        _fcntl.flock(fileobj.fileno(), _fcntl.LOCK_EX)
        return
    global _FLOCK_WARNED
    if not _FLOCK_WARNED:
        import warnings
        warnings.warn(
            "fcntl unavailable on this platform — the obligation-ledger cross-process write fence is "
            "NOT enforced; concurrent multi-process appends could fork the chain. Single-process use "
            "is safe.", RuntimeWarning, stacklevel=2)
        _FLOCK_WARNED = True


def _flock_un(fileobj) -> None:
    if _HAS_FCNTL:
        _fcntl.flock(fileobj.fileno(), _fcntl.LOCK_UN)

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


def _node_default_root() -> Path:
    """The node's canonical ledger root: the live review queue (memory/obligations/atrium_review), where
    the real cards live. The ONE default every node-side reader/writer falls back to when the env is
    unset — so an env-unset API serves the real chain instead of an empty parent path."""
    return _default_root() / "atrium_review"


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


def get_ledger_root(explicit: Optional[os.PathLike | str] = None,
                    default: Optional[os.PathLike | str] = None) -> Path:
    """THE single ledger-root resolver (audit 2026-06-13). Resolution order:
        explicit arg → OBLIGATION_LEDGER_ROOT env → caller `default` → node canonical (atrium_review).
    Every node-side site (API deps, bell executor, /export, /actions, review_ready) routes through this
    so the API and the bell executor can NEVER resolve different roots — the split-brain that landed
    approve in one chain and close in another. Boundary-checked exactly like _resolve_root."""
    chosen = explicit or os.environ.get(ENV_ROOT) or default or _node_default_root()
    return _resolve_root(chosen)


def _assert_source_ref_resolves(source_ref: str) -> None:
    """R22-3 provenance rule (GB): a path-like `source_ref` MUST resolve — the file exists, and if a
    `#"quoted text"` passage is appended, that text is present — else raise. A citation is never written
    false. Symbolic refs (no path separator + extension, e.g. 'B11:veto-chapter') are accepted as-is
    (not a file claim, so not falsifiable here)."""
    head, _, tail = source_ref.partition("#")
    path_part = head.strip()
    # Compound ref (audit 2026-06-13 W5 #6): GB feed refs are "<path> + <annotation> + …" where the
    # LEADING token is the file claim and the ` + …` tail is symbolic provenance (e.g. 'B51 delta',
    # 'THREAD[67]'). Validate only the leading file token; the annotations are not file claims, so a real
    # compound ref is never falsely rejected.
    path_part = path_part.split(" + ", 1)[0].strip()
    passage = tail.strip().strip('"') if tail else None
    last = path_part.rsplit("/", 1)[-1]
    if "/" not in path_part or "." not in last:
        return  # symbolic ref — not a file claim
    # Runs-anywhere (audit 2026-06-13): resolve against config-derived roots, not hardcoded operator
    # vault literals (a genuinely-resolvable passage failed on any other host). Falls back to cwd +
    # repo-root; config getters return None on a vault-less host (then only cwd/repo are tried).
    from .. import config  # noqa: PLC0415 — lazy to avoid import cycles
    roots = [Path.cwd(), Path(__file__).resolve().parents[3]]
    books = config.get_books_kdp_root()
    if books:
        roots += [Path(books), Path(books).parent]    # kdp root + the vault root above it
    plays = config.get_playbooks_dir()
    if plays:
        roots.append(Path(plays))
    resolved = next((r / path_part for r in roots if (r / path_part).is_file()), None)
    if resolved is None:
        raise ValueError(
            f"R22-3 provenance: source_ref '{path_part}' does not resolve to a file under known "
            f"roots — a citation is never written false."
        )
    if passage and passage not in resolved.read_text(encoding="utf-8", errors="ignore"):
        raise ValueError(
            f"R22-3 provenance: cited passage not present in '{path_part}' — the source must say it."
        )


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
        # Order-aware (THREAD [245]): the LAST close/reopen event governs. A corrective `reopen`
        # appended after a `credit` returns the obligation to open — consistent with replay().
        state = None
        for e in self._entries():
            if e.get("type") == "credit" and e.get("closes") == obligation_id:
                state = "closed"
            elif e.get("type") == "reopen" and e.get("reopens") == obligation_id:
                state = "open"
        return state == "closed"

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
            _flock_ex(lock)
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
                _flock_un(lock)
        return entry

    def repair_chain(self) -> dict:
        """Re-link an already-forked chain (audit chain-repair command). Reads every entry in file order,
        recomputes prev_hash + hash so the chain is internally valid again, and rewrites the ndjson — backing
        up the original to obligations.ndjson.forked.<n> first. Held under the same write-fence. The repaired
        chain re-hashes content (the fork already broke cryptographic continuity); the backup preserves the
        raw forked record for audit. Returns {repaired, was_valid, entries, backup}."""
        lock_path = self.root / "obligations.lock"
        with open(lock_path, "a+") as lock:
            _flock_ex(lock)
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
                _flock_un(lock)

    # ── lifecycle ─────────────────────────────────────────────────────
    def open(self, title: str, owner: Optional[str] = None,
             classification: str = "C2", intent: Optional[str] = None,
             ref: Optional[str] = None, material: bool = False,
             lgp: Optional[dict] = None, next_gate: Optional[str] = None,
             category: Optional[str] = None, lane: Optional[str] = None,
             requires_attestation: Optional[list] = None, veto_window: Optional[str] = None) -> dict:
        """Open an obligation = a DRAFT action-proposal (debit). CYL-006: starts draft.

        material=True ⇒ a gated ledger requires human approval (breath-gate) before close.
        lgp (P0-2) ⇒ optional families-first contribution that travels WITH the obligation, e.g.
          {"alignment_score": "0.92", "families_first_impact": "+18% effective purchasing power (C2F)"}.
        next_gate ⇒ human-readable next human-disposition point (mirrors series_roadmap.yaml).
        category / lane (A2 capture classification) ⇒ the one-tap capture category (typo/wording/
          structure/technical/judgment) and the lane it routed to (batch | discrete). Travel WITH the
          obligation so triage never lands downstream — the 36% 'other' is killed at capture, not after.
        """
        # Resolve-at-entry (audit 2026-06-13): a path-like `ref` sealed at open() must resolve, the same
        # resolve-or-symbolic-or-raise rule close()'s source_ref obeys — a pointer is never written false.
        # Symbolic refs (e.g. 'viewer:B12 ch3', 'review_ready:vol_01') pass through untouched.
        if ref:
            _assert_source_ref_resolves(ref)
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
        if requires_attestation:        # R22-4: joint-attestation action class (≥N roles must attest)
            entry["requires_attestation"] = list(requires_attestation)
        if veto_window:
            entry["veto_window"] = veto_window
        if next_gate:
            entry["next_gate"] = next_gate
        if category:
            entry["category"] = category   # A2: capture-time classification travels with the obligation
        if lane:
            entry["lane"] = lane           # A2: batch (born-approved mechanical) | discrete (gated)
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
              closed_by: Optional[str] = None, rejected: bool = False,
              source_ref: Optional[str] = None, method: Optional[str] = None,
              authorized_by_spec: Optional[str] = None) -> dict:
        """Close an obligation = credit, with evidence + a minted receipt.

        Rejects E0 (claim-only) when require_e1 is True (the default for material obligations).
        rejected=True ⇒ this close is a human REFUSAL, not an execution. The breath-gate guards
        execution (work done), not refusal — a rejection is itself a valid human disposition, so a
        material obligation may be rejected without a prior approve() (human primacy: 'no' needs no gate).

        R22-3 (source-citation lineage): optional `source_ref` (the book passage / file that authorized
        the action), `method`, and `authorized_by_spec` carry *why / from-what* onto the receipt — not just
        *what*. Provenance rule (GB): a path-like `source_ref` MUST resolve (file exists; if `#"text"` is
        appended, that text is present) or close() raises — a pointer is never written false. These fields
        are additive + forward-compatible: receipts without them are unchanged and still valid.
        """
        if source_ref:
            _assert_source_ref_resolves(source_ref)
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
        # Human primacy (CYL-006): a MATERIAL obligation cannot EXECUTE (close with work-done) until it
        # has cleared the breath-gate. A rejection is exempt — refusing is itself the human disposition.
        # FAIL-CLOSED (audit 2026-06-13 MED): the guard no longer depends on `self.gate is not None`. A
        # gate-less ledger (e.g. the bell executor's raw ObligationLedger) must NOT mean "no gate to
        # satisfy" — it means "cannot self-approve here". The approval lives on the shared chain (the API
        # approves on the gated ledger before spawning the executor), so `_is_approved` still passes for
        # realized paths; a direct CLI close on an un-approved material packet is now correctly blocked.
        if (ob and ob.get("material") and not rejected and not self._is_approved(obligation_id)):
            raise PermissionError(
                f"'{obligation_id}' is material and has not cleared the breath-gate; "
                f"call approve() (human disposition) before close."
            )
        # R22-4: a joint-attestation action cannot EXECUTE until all required roles attest AND no
        # standing veto (default-deny). A rejection (refusal) is exempt — 'no' needs no attestation.
        if ob and ob.get("requires_attestation") and not rejected:
            st = self.attestation_status(obligation_id)
            if st["vetoed"]:
                raise PermissionError(
                    f"'{obligation_id}' is VETOED by {st['standing_vetoes']} ({st['veto_reasons']}); "
                    f"default-deny — cannot execute. Close as rejected to record the denial."
                )
            if st["missing"]:
                raise PermissionError(
                    f"'{obligation_id}' requires attestation from {st['missing']} "
                    f"(have {st['attested']}); cannot execute on partial attestation."
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
        # R22-3: provenance lineage — additive, only when supplied (resolves-or-absent, never false).
        for _k, _v in (("source_ref", source_ref), ("method", method),
                       ("authorized_by_spec", authorized_by_spec)):
            if _v:
                receipt[_k] = _v
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

    def reopen(self, obligation_id: str, reason: str, reopened_by: Optional[str] = None) -> dict:
        """Corrective reopen — append a `reopen` event citing WHY a previously-closed obligation
        must return to the open/undisposed state. Preserves the original obligation's id + receipts
        (it is NOT re-minted): the chain confesses the correction rather than hiding it. THREAD [245]:
        used to formally reopen the 42 KM comments that were closed without disposition, so the ledger
        and the derived sittings view speak one truth."""
        ob = self._get(obligation_id)
        if ob is None:
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        entry = {
            "type": "reopen",
            "id": _entry_id(),
            "reopens": obligation_id,
            "reason": reason,
            "reopened_by": reopened_by or self.principal_id,
            "principal_id": self.principal_id,
            "timestamp": _now(),
        }
        return self._append(entry)

    # ── R22-4: joint attestation + cross-role veto ────────────────────
    def attest(self, obligation_id: str, role: str, attested_by: Optional[str] = None) -> dict:
        """A role attests a joint-attestation action. Composes toward `requires_attestation`."""
        if self._get(obligation_id) is None:
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        return self._append({"type": "attest", "attests": obligation_id, "role": role,
                             "attested_by": attested_by or self.principal_id, "timestamp": _now()})

    def veto(self, obligation_id: str, role: str, reason: str,
             vetoed_by: Optional[str] = None) -> dict:
        """Any qualified role structurally VETOES before execute. Default-deny while unresolved (loud)."""
        if self._get(obligation_id) is None:
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        if not reason:
            raise ValueError("veto requires a reason (loud, recorded)")
        return self._append({"type": "veto", "vetoes": obligation_id, "role": role, "reason": reason,
                             "vetoed_by": vetoed_by or self.principal_id, "timestamp": _now()})

    def clear_veto(self, obligation_id: str, role: str, cleared_by: Optional[str] = None) -> dict:
        """Withdraw a veto (the vetoing role stands down). Order-aware: last veto/clear governs."""
        return self._append({"type": "veto_clear", "clears_veto": obligation_id, "role": role,
                            "cleared_by": cleared_by or self.principal_id, "timestamp": _now()})

    def attestation_status(self, obligation_id: str) -> dict:
        """Replay attestations + vetoes for an obligation (ORDER-AWARE: the last veto/clear per role
        governs — mirrors the reopen/_is_closed fix). Returns the veto reconstruction + can_execute.
        Default-deny: any standing veto ⇒ vetoed=True ⇒ cannot execute."""
        ob = self._get(obligation_id) or {}
        required = set(ob.get("requires_attestation") or [])
        attested, veto_state = set(), {}   # role -> 'veto'/'clear' (last wins, in chain order)
        veto_reasons = {}
        for e in self._entries():
            t = e.get("type")
            if t == "attest" and e.get("attests") == obligation_id:
                attested.add(e.get("role"))
            elif t == "veto" and e.get("vetoes") == obligation_id:
                veto_state[e.get("role")] = "veto"; veto_reasons[e.get("role")] = e.get("reason")
            elif t == "veto_clear" and e.get("clears_veto") == obligation_id:
                veto_state[e.get("role")] = "clear"
        standing_vetoes = [r for r, s in veto_state.items() if s == "veto"]
        missing = sorted(required - attested)
        vetoed = bool(standing_vetoes)
        return {
            "required": sorted(required), "attested": sorted(attested), "missing": missing,
            "vetoed": vetoed, "standing_vetoes": sorted(standing_vetoes),
            "veto_reasons": {r: veto_reasons[r] for r in standing_vetoes},
            "can_execute": (not vetoed) and (not missing),
        }

    # ── replay + materialized views ───────────────────────────────────
    def replay(self) -> dict:
        """Reconstruct state from the append-only chain.

        Memoized on _stat_key (audit 2026-06-13 perf): GET /obligations derived open/status/by_owner
        from up to 4 replays per request; now one materialization per chain-state, invalidated when the
        file changes (the SAME trust key _entries/verify_chain use — no weaker than the parse cache)."""
        key = self._stat_key()
        cache = getattr(self, "_replay_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        entries = self._entries()
        debits = {e["id"]: e for e in entries if e.get("type") == "debit"}
        closed = {e["closes"] for e in entries if e.get("type") == "credit"}
        # Corrective reopens (THREAD [245]): a reopen event after a close returns the obligation to
        # the open set. Order-aware so a later re-close still wins (last close/reopen per id governs).
        last_state: dict[str, str] = {}
        for e in entries:
            if e.get("type") == "credit":
                last_state[e["closes"]] = "closed"
            elif e.get("type") == "reopen":
                last_state[e["reopens"]] = "open"
        closed = {oid for oid in closed if last_state.get(oid) != "open"}
        # Only approvals actually DISPOSITIONED 'approved' count (audit fix): a denied/pending
        # approval entry must not flip a draft to approved in the replay view. Mirrors _is_approved.
        approved = {e["approves"] for e in entries
                    if e.get("type") == "approval" and e.get("disposition", "approved") == "approved"}
        for oid in approved:
            if oid in debits:
                debits[oid] = {**debits[oid], "draft": False, "approved": True}
        open_obs = [d for oid, d in debits.items() if oid not in closed]
        closed_obs = [d for oid, d in debits.items() if oid in closed]
        result = {"open": open_obs, "closed": closed_obs, "all": list(debits.values())}
        self._replay_cache = (key, result)
        return result

    def open_obligations(self, owner: Optional[str] = None) -> list[dict]:
        obs = self.replay()["open"]
        return [o for o in obs if o["owner"] == owner] if owner else obs

    def by_status(self) -> dict:
        st = self.replay()
        return {"open": len(st["open"]), "closed": len(st["closed"]), "total": len(st["all"])}

    def by_owner(self) -> dict:
        """Per-owner open/closed counts derived from the ORDER-AWARE replay (audit 2026-06-13).

        The old impl derived 'closed' from raw `credit` entries, so a reopened-not-reclosed obligation
        (after reopen()) was double-counted as closed — the per-owner counts lied after any reopen (the
        Open Card Parity disease in miniature). Deriving from replay()'s reopen-aware open/closed sets
        (one memoized pass) keeps the view in lockstep with the chain's true state."""
        st = self.replay()
        open_ids = {o["id"] for o in st["open"]}
        out: dict[str, dict] = {}
        for o in st["all"]:
            bucket = out.setdefault(o["owner"], {"open": 0, "closed": 0})
            bucket["open" if o["id"] in open_ids else "closed"] += 1
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
