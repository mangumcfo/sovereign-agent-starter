"""ObligationLedger — node-local B32 obligation ledger (R-23 Phase 1).

A dr/cr, append-only, hash-chained, evidence-tiered obligation ledger that lives INSIDE the sovereign
node, on its OWN storage root — fully self-contained, never touching the live the node cylinder chain.

Lifecycle: open(...) -> DRAFT debit [CYL-006] · approve(id) -> the gate (Phase 2 wires the node breath-
gate) · close(id, evidence) -> credit (evidence tier-classified, receipt minted). All appended to one
NDJSON chain (prev_hash linked); state reconstructed by replay(). Concerns extracted to sibling modules
(_util/_locking/evidence/roots/provenance/projection) per audit 2026-06-16 #6 — re-exported below.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Optional

from ..ndjson import read_ndjson  # the ONE tolerant ndjson reader (Universalize Wave §1)
# Extracted concerns (audit 2026-06-16 #6 — extraction, not abstraction). The names are RE-EXPORTED here
# (and in __all__) so the public surface `from .ledger import …` and the package __init__ are unchanged.
from ._util import _now, _hash, _entry_id, _receipt_id
from ._locking import _flock_ex, _flock_un
from .evidence import EvidenceTier, classify_evidence
from .roots import LedgerBoundaryError, get_ledger_root, _resolve_root
from .provenance import _assert_source_ref_resolves
from . import projection as _proj
from . import mandate_guard as _mandate_guard
from . import quorum_guard as _quorum_guard


class AlreadyClosedError(RuntimeError):
    """Raised by close() when an obligation has already been credited/closed (audit guard)."""


__all__ = [
    "ObligationLedger", "AlreadyClosedError", "EvidenceTier", "classify_evidence",
    "LedgerBoundaryError", "get_ledger_root",
]


class ObligationLedger:
    """Append-only, hash-chained dr/cr obligation ledger on a node-local root."""

    def __init__(self, root: Optional[os.PathLike | str] = None,
                 principal_id: str = "node",
                 gate=None, attestor=None,
                 class_quorum: Optional[dict] = None,
                 node_identity: Optional[dict] = None):
        """gate / attestor are OPTIONAL duck-typed callables (thin-waist injection):
          gate(action, obligation) -> {"status": "approved"|"denied", ...} — breath-gate disposition (Phase 2).
          attestor(action_class, principal_id, payload, result_summary) -> {"receipt_hash": str, ...}.
        Both default None → fully standalone (Phase-1; tests stay green). node_integration.wire_node_ledger
        adapts the node's real HumanApprovalGate + ComplianceEngine into these contracts."""
        self.root = _resolve_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "obligations.ndjson"
        self.principal_id = principal_id
        self.gate = gate
        self.attestor = attestor
        # Charter decisions supplied at node standup (both optional; absent ⇒ prior behavior unchanged):
        #   class_quorum  — {classification: min approval quorum} (S2-V3 Ch 5 "per proposal class");
        #                   a FLOOR resolved + stamped on the debit at open(), so is_approved() stays
        #                   a pure replay over committed entries.
        #   node_identity — {principal_id: [mandates held]} (S2-V4 Ch 2 §215); held mandates RESOLVE
        #                   from identity at approve() and are stamped on the approval entry.
        self.class_quorum = dict(class_quorum) if class_quorum else None
        self.node_identity = dict(node_identity) if node_identity else None

    # ── chain primitives ──────────────────────────────────────────────
    _ENTRIES_HEAD = 256   # bytes of the file head used to detect a rewrite vs a pure append

    def _entries(self) -> list[dict]:
        # Parse-cache keyed by (st_mtime_ns, st_size); re-reads only on change. APPEND-AWARE TAIL PARSE
        # (audit 2026-06-13c H3/#18): _append calls this INSIDE the write-flock, so on a pure grow we seek
        # to the last-parsed byte offset and parse ONLY the new tail (O(Δ), not O(n)/write). A head-
        # fingerprint guard detects a rewrite (repair_chain rehashes → head changes) → full re-parse.
        # Cache tuple: (entries, key, parsed_byte_size, head_bytes).
        if not self.path.exists():
            self._entries_cache = ([], None, 0, b"")
            self._chain_status = read_ndjson(self.path)  # clean empty read
            return []
        st = self.path.stat()
        key = (st.st_mtime_ns, st.st_size)
        cache = getattr(self, "_entries_cache", None)
        if cache is not None and cache[1] == key:
            return cache[0]
        if cache is not None:
            prev_entries, _prev_key, prev_size, prev_head = cache
            if 0 < prev_size < st.st_size:   # the file only GREW — candidate for a tail parse
                try:
                    with self.path.open("rb") as f:
                        head = f.read(self._ENTRIES_HEAD)
                        if head == prev_head:           # head unchanged → pure append, not a rewrite
                            f.seek(prev_size)
                            tail = f.read().decode("utf-8")
                            new = [json.loads(s) for s in tail.splitlines() if s.strip()]
                            out = prev_entries + new
                            self._entries_cache = (out, key, st.st_size, prev_head)
                            return out
                except (OSError, ValueError, UnicodeDecodeError):
                    pass   # boundary/rewrite scramble OR truncated tail → full TOLERANT re-parse below
        # FULL tolerant parse via the ONE gateway (Universalize Wave §1/G2): a truncated TRAILING line is
        # quarantined (the chain still loads on its clean prefix, and repair_chain can rewrite it); a corrupt
        # MIDDLE line flags chain_corrupt so verify_chain() returns False and routes degrade loudly.
        res = read_ndjson(self.path)
        self._chain_status = res
        out = res.entries
        with self.path.open("rb") as f:
            head = f.read(self._ENTRIES_HEAD)
        # When a tail was quarantined or a hole was found, do NOT cache a byte offset — force a full
        # re-parse on the next change so the completed/repaired line is re-read (disable the tail fast path).
        parsed_size = 0 if (res.repair_required or res.chain_corrupt) else key[1]
        self._entries_cache = (out, key, parsed_size, head)
        return out

    def iter_entries(self):
        """Public read-gateway over the chain (audit 2026-06-13c #15): yields a COPY of each raw entry.
        Five sites previously reached into the private `_entries()` and hardcoded the entry-type
        vocabulary (a shipped bug guessed 'open' vs 'debit'); they route through this instead."""
        for e in self._entries():
            yield dict(e)

    def refs(self, type: str = "debit") -> set:
        """The set of non-empty `ref` strings for entries of the given chain type (default 'debit').
        Memoized on (_stat_key, type) (Universalize Wave §3): GET /hopper calls this every poll to dedup
        already-packeted cards — no need to re-scan the chain set when the file hasn't changed."""
        cache_key = (self._stat_key(), type)
        cache = getattr(self, "_refs_cache", None)
        if cache is not None and cache[0] == cache_key:
            return cache[1]
        val = _proj.refs(self._entries(), type)
        self._refs_cache = (cache_key, val)
        return val

    def _is_closed(self, obligation_id: str) -> bool:
        return _proj.is_closed(self._entries(), obligation_id)

    def _stat_key(self) -> tuple:
        """Identity of the on-disk chain: (mtime_ns, size). This is the SAME trust key `_entries()`
        uses for its parse cache — so memoizing verify_chain on it is no weaker than the parse cache
        already is. A genuine append/edit bumps the key; an unchanged file is treated as unchanged."""
        if not self.path.exists():
            return ("genesis", 0)
        st = self.path.stat()
        return (st.st_mtime_ns, st.st_size)

    @contextmanager
    def _write_fence(self):
        """The exclusive flock over the read-tail-THROUGH-write critical section (audit 2026-06-10): the
        ONE lock both _append and repair_chain hold so two appenders can never read the same tail, compute
        the same prev_hash, and permanently fork the chain. The sidecar .lock is advisory + not in the chain."""
        lock_path = self.root / "obligations.lock"
        with open(lock_path, "a+") as lock:
            _flock_ex(lock)
            try:
                yield
            finally:
                _flock_un(lock)

    def _append(self, entry: dict) -> dict:
        # prev_hash needs the tail read INSIDE the fence (O_APPEND alone is insufficient): every writer
        # (threads + cross-process scripts on the shared root) funnels through _write_fence(), closing the
        # fork race. The pre-append verify cache key must match the current file identity (any out-of-band
        # change bumps the key → full re-verify catches the tamper).
        with self._write_fence():
            pre_cache = getattr(self, "_verify_cache", None)
            pre_valid = bool(pre_cache and pre_cache[0] == self._stat_key() and pre_cache[1])
            entries = self._entries()
            entry["prev_hash"] = entries[-1]["hash"] if entries else "genesis"
            entry["hash"] = _hash({k: v for k, v in entry.items() if k != "hash"})
            with self.path.open("a") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            # Incremental verify frontier: a correctly-linked entry on a known-valid chain leaves it valid —
            # advance the cached verdict WITHOUT a re-hash; else drop the cache so next verify recomputes.
            self._verify_cache = (self._stat_key(), True) if pre_valid else None
        return entry

    def repair_chain(self) -> dict:
        """Re-link an already-forked chain (audit chain-repair command). Reads every entry in file order,
        recomputes prev_hash + hash so the chain is internally valid again, and rewrites the ndjson — backing
        up the original to obligations.ndjson.forked.<n> first. Held under the same write-fence. The repaired
        chain re-hashes content (the fork already broke cryptographic continuity); the backup preserves the
        raw forked record for audit. Returns {repaired, was_valid, entries, backup}.

        Universalize Wave §1/G2: repair also survives + heals a TRUNCATED TRAILING line. The tolerant reader
        loads the clean prefix (dropping the dangling partial line) instead of raising — so repair_chain can
        run at all — and a dangling tail forces a rewrite even when the clean prefix verifies, because leaving
        the partial line in place would turn it into a corrupt MIDDLE line on the next append."""
        with self._write_fence():
            entries = self._entries()                       # populates self._chain_status
            status = getattr(self, "_chain_status", None)
            truncated_tail = bool(status and status.repair_required and not status.chain_corrupt)
            if self.verify_chain() and not truncated_tail:
                return {"repaired": False, "was_valid": True, "entries": len(entries), "backup": None}
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

    # ── lifecycle ─────────────────────────────────────────────────────
    def open(self, title: str, owner: Optional[str] = None,
             classification: str = "C2", intent: Optional[str] = None,
             ref: Optional[str] = None, material: bool = False,
             lgp: Optional[dict] = None, next_gate: Optional[str] = None,
             category: Optional[str] = None, lane: Optional[str] = None,
             requires_attestation: Optional[list] = None, veto_window: Optional[str] = None,
             mandate: Optional[str] = None, quorum: Optional[int] = None) -> dict:
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
        if mandate:
            entry["mandate"] = mandate      # Slice 2.1: constitutional mandate this obligation is scoped
            #                                 to (S2-V4 Ch 2). Absent ⇒ unscoped / single-mandate sovereign.
        # Slice 2.2 + class-level config (S2-V3 Ch 5 "the operator sets it per proposal class"):
        # the Charter's class_quorum mapping is a FLOOR for MATERIAL obligations — a declaration may
        # raise the bar, never undercut it. Resolved HERE and stamped on the debit so is_approved()
        # remains a pure replay over committed entries (nothing external at read time). Non-material
        # keeps quorum-1 (the guard only enforces quorum on the material class — same boundary as AH-1).
        q_floor = _quorum_guard.class_quorum_floor(self.class_quorum, classification) if material else 1
        q_eff = _quorum_guard.effective_quorum(quorum, q_floor)
        if q_eff > 1:
            entry["quorum"] = q_eff         # N distinct gate-valid approvers, opener excluded.
            if q_floor > 1 and q_eff == q_floor:
                entry["quorum_source"] = f"class:{classification}"  # the Charter's class floor set the bar
        return self._append(entry)

    # ── lookups ───────────────────────────────────────────────────────
    def _get(self, obligation_id: str) -> Optional[dict]:
        for e in self._entries():
            if e.get("type") == "debit" and e.get("id") == obligation_id:
                return e
        return None

    def _is_approved(self, obligation_id: str) -> bool:
        return _proj.is_approved(self._entries(), obligation_id)

    def approve(self, obligation_id: str, approved_by: str,
                rationale: str = "",
                held_mandates: Optional[list] = None,
                cross_mandate_auth: Optional[dict] = None) -> dict:
        """Approve a draft via the breath-gate. If a `gate` is injected, the disposition
        is the gate's verdict (human primacy); a DENY raises and is recorded.

        AH-1 (Option A, the operator-ratified 2026-07-08): a gate-less ledger CANNOT mint an "approved"
        disposition for a MATERIAL obligation — it is DENIED, fail-closed, and recorded. With no
        human breath-gate injected there is no authority to approve here, so the sealed claim
        (material events "structurally barred from any GREEN auto-flow") is an architectural
        invariant, not a wiring convention. Non-material keeps the permissive default (GREEN routine
        actions were never in scope of the bar — see arc GREEN-non-material autorun).

        Slice 2.1 (cross-mandate blocking, S2-V4 Federated Sovereignty Ch 2): if the obligation is
        SCOPED to a mandate (`mandate` field) and MATERIAL, the acting principal must HOLD that mandate
        — supplied as `held_mandates` — or carry an explicit `cross_mandate_auth`. A principal holding
        mandate A acting on an obligation scoped to mandate B they do not hold is DENIED, fail-closed
        (recorded + raises), ADDITIONAL to and composed with AH-1. Unscoped obligations are unaffected
        (single-mandate sovereign default). See obligations/mandate_guard.py for the representation
        assumption (held mandates supplied at the action site; the book's full cross-mandate ceremony
        — the 3-receipt witness — is the heavier designed-toward form)."""
        ob = self._require(obligation_id)  # audit guard: no orphan approvals (also: material-class check)
        if self._is_closed(obligation_id):
            raise AlreadyClosedError(f"obligation '{obligation_id}' is already closed — cannot approve")
        disposition, gate_meta = "approved", None
        if self.gate is not None:
            verdict = self.gate("approve", {"id": obligation_id, "approved_by": approved_by,
                                            "rationale": rationale}) or {}
            disposition = verdict.get("status", "approved")
            gate_meta = verdict
        elif ob.get("material"):
            # FAIL-CLOSED (AH-1): gate-less + material ⇒ no human gate to authorize ⇒ DENY. Recorded
            # loudly on the chain (evidence trail), then the raise below fires (existing failure idiom).
            disposition = "denied"
            gate_meta = {"status": "denied", "real": False,
                         "reason": "gate-less ledger cannot mint a material approval — structurally "
                                   "barred from GREEN auto-flow (inject a human breath-gate to approve)"}
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
        # Record the acting principal's mandate context ON the approval so is_approved()'s replay reads
        # committed data (same idiom as AH-1's recorded gate) — never external, self-asserted-at-write.
        # Held-mandate resolution from node identity (S2-V4 Ch 2 §215): when the acting principal is
        # KNOWN to the node_identity registry, identity GOVERNS — the registry's list is what gets
        # stamped, and a self-declaration claiming a mandate identity does not grant is DENIED below.
        resolved_held, held_source, overclaimed = _mandate_guard.resolve_held_mandates(
            self.node_identity, approved_by, held_mandates)
        if held_source == "node_identity":
            entry["held_mandates"] = resolved_held
            entry["held_mandates_source"] = "node_identity"
        elif held_mandates is not None:
            entry["held_mandates"] = list(held_mandates)
        if cross_mandate_auth is not None:
            entry["cross_mandate_auth"] = cross_mandate_auth
        # FAIL-CLOSED (held-mandate resolution): a declared mandate the principal's node identity does
        # not hold is a barred self-elevation — DENY + record, composed with AH-1 and the 2.1 guard.
        if disposition == "approved" and overclaimed:
            disposition = "denied"
            entry["disposition"] = "denied"
            entry["gate"] = {"status": "denied", "real": False,
                             "reason": f"held-mandate overclaim barred: declaration claims {overclaimed} "
                                       f"but node identity for '{approved_by}' holds {resolved_held} — "
                                       f"a mandate is carried by identity, never self-declared (S2-V4 Ch 2)"}
        # FAIL-CLOSED (Slice 2.1): a material obligation scoped to a mandate the acting principal does
        # not hold is a barred cross-mandate act — DENY (composed with, never weakening, AH-1 above).
        if disposition == "approved" and ob.get("material") \
                and not _mandate_guard.approval_holds_mandate(ob, entry):
            disposition = "denied"
            entry["disposition"] = "denied"
            entry["gate"] = {"status": "denied", "real": False,
                             "reason": f"cross-mandate act barred: obligation scoped to mandate "
                                       f"'{ob.get('mandate')}'; acting principal does not hold it "
                                       f"(no held_mandates match, no explicit cross_mandate_auth) — "
                                       f"cross-mandate operations require constitutional ceremony (S2-V4 Ch 2)"}
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

        Rejects E0 (claim-only) when require_e1 (default for material). rejected=True ⇒ a human REFUSAL,
        not an execution: the breath-gate guards execution, not refusal, so a material obligation may be
        rejected without a prior approve() ('no' needs no gate). R22-3: optional source_ref / method /
        authorized_by_spec carry *why / from-what* onto the receipt (additive); a path-like source_ref MUST
        resolve (file exists; an appended #"text" passage is present) or close() raises — never written false.
        """
        if source_ref:
            _assert_source_ref_resolves(source_ref)
        ob = self._require(obligation_id)  # existence/closed guards FIRST — 'not found' beats 'bad evidence'
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

    def _require(self, obligation_id: str) -> dict:
        """Existence guard shared by the lifecycle writes — return the obligation or raise KeyError."""
        ob = self._get(obligation_id)
        if ob is None:
            raise KeyError(f"obligation '{obligation_id}' does not exist")
        return ob

    def reopen(self, obligation_id: str, reason: str, reopened_by: Optional[str] = None) -> dict:
        """Corrective reopen — append a `reopen` event citing WHY a closed obligation returns to open.
        Preserves the original id + receipts (NOT re-minted): the chain confesses the correction (THREAD
        [245]: reopened the 42 the operator comments closed without disposition so ledger + sittings speak one truth)."""
        self._require(obligation_id)
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
        self._require(obligation_id)
        return self._append({"type": "attest", "attests": obligation_id, "role": role,
                             "attested_by": attested_by or self.principal_id, "timestamp": _now()})

    def veto(self, obligation_id: str, role: str, reason: str,
             vetoed_by: Optional[str] = None) -> dict:
        """Any qualified role structurally VETOES before execute. Default-deny while unresolved (loud)."""
        self._require(obligation_id)
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
        required = (self._get(obligation_id) or {}).get("requires_attestation") or []
        return _proj.attestation_status(self._entries(), obligation_id, set(required))

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
        result = _proj.replay(self._entries())
        self._replay_cache = (key, result)
        return result

    def open_obligations(self, owner: Optional[str] = None) -> list[dict]:
        return _proj.open_obligations(self.replay(), owner)

    def by_status(self) -> dict:
        return _proj.by_status(self.replay())

    def by_owner(self) -> dict:
        """Per-owner open/closed counts from the ORDER-AWARE replay (reopen-aware: a reopened-not-reclosed
        obligation is NOT double-counted as closed — the Open Card Parity disease in miniature)."""
        return _proj.by_owner(self.replay())

    def full_log(self) -> list[dict]:
        """
        Per-obligation materialized record incl. approval + close evidence/receipt — for
        read-only drilldowns (the Atrium book↔code / review lens). Newest first.

        Memoized on _stat_key (audit 2026-06-13c #11) — the one un-memoized ledger view, backing the
        polled GET /obligations/log; now caches like replay()/verify_chain(), re-deriving only on change.
        """
        key = self._stat_key()
        cache = getattr(self, "_full_log_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        out = _proj.full_log(self._entries())
        self._full_log_cache = (key, out)
        return out

    def verify_chain(self) -> bool:
        """True iff every prev_hash + hash is intact. INCREMENTAL: memoized on the file identity key
        (_stat_key), so the hot path (many chain_ok reads between writes) is O(1); any change to the file
        bumps the key → full recompute, so tampering is caught the moment the file differs (no weaker than
        the _entries() parse cache, which trusts the same key). _append advances the frontier in-lock."""
        key = self._stat_key()
        cache = getattr(self, "_verify_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        ok = self._recompute_chain()
        self._verify_cache = (key, ok)
        return ok

    def _recompute_chain(self) -> bool:
        """Full hash-walk from genesis — the O(n) ground truth behind the memoized verify_chain."""
        entries = self._entries()   # populates self._chain_status
        # A corrupt MIDDLE line is a committed hole (Universalize Wave §1/G2) ⇒ invalid regardless of the
        # surviving links; a truncated trailing line (repair_required, not chain_corrupt) can still verify.
        status = getattr(self, "_chain_status", None)
        return _proj.recompute_chain(entries, bool(status and status.chain_corrupt))

    def manifest(self) -> dict:
        """One-glance proof of ledger state (P0-1): after any open/approve/close the last_hash changes +
        the obligation counts move — cryptographic + countable proof the agent's state updated."""
        return _proj.manifest(self._entries(), str(self.path), self.by_status(), self.verify_chain())
