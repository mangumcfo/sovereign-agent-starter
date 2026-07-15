"""Pure projection functions over an obligation-chain `entries` list — extracted verbatim from the
ObligationLedger read methods (audit 2026-06-16 #6, extraction not abstraction).

These are STATELESS and deterministic: same entries -> same output. All memoization stays on the
ObligationLedger instance (the class methods are thin wrappers that call these inside their caches), so
caching behavior is byte-identical. No imports from ledger.py (no cycle); only _util (chain hash) and
mandate_guard (a sibling pure predicate module — no cycle) are imported.
"""
from __future__ import annotations

from . import mandate_guard as _mguard
from . import quorum_guard as _qguard
from . import witness as _witness
from ._util import _hash


def is_closed(entries: list[dict], obligation_id: str) -> bool:
    # Order-aware (THREAD [245]): the LAST close/reopen event governs. A corrective `reopen`
    # appended after a `credit` returns the obligation to open — consistent with replay().
    state = None
    for e in entries:
        if e.get("type") == "credit" and e.get("closes") == obligation_id:
            state = "closed"
        elif e.get("type") == "reopen" and e.get("reopens") == obligation_id:
            state = "open"
    return state == "closed"


def is_approved(entries: list[dict], obligation_id: str) -> bool:
    # AH-1 (Option A, the operator-ratified 2026-07-08): opener ≠ approver for the MATERIAL class. A material
    # obligation self-approved by its own owner does NOT clear the breath-gate — UNLESS a real human
    # breath-gate dispositioned it (gate.real). That exception is load-bearing: on a single-owner
    # sovereign node the operator's principal legitimately BOTH proposes and disposes THROUGH the
    # authenticated, owner-gated /approve route (a real gate, real=True) — the human IS acting. A bare
    # or rubber-stamped self-approval (no real gate) is barred; non-material is the simple check.
    debit = next((e for e in entries
                  if e.get("type") == "debit" and e.get("id") == obligation_id), None)
    material = bool(debit and debit.get("material"))
    owner = debit.get("owner") if debit else None
    # Slice 2.2 (multi-role quorum, S2-V3 Ch 5): a material obligation declaring quorum N needs N
    # DISTINCT gate-valid approvers; the opener never counts toward a multi-party quorum (declaring
    # quorum > 1 is the operator's opt-in to multi-party review — "reviewing roles" review someone
    # else's proposal). quorum 1 (the default) is byte-identical to the pre-slice single-approval flow.
    quorum = _qguard.required_quorum(debit) if material else 1
    approvers: set = set()
    for e in entries:
        if e.get("type") != "approval" or e.get("approves") != obligation_id:
            continue
        if e.get("disposition", "approved") != "approved":
            continue
        if material and owner is not None and e.get("approved_by") == owner:
            gate = e.get("gate")
            if not (isinstance(gate, dict) and gate.get("real")):
                continue  # self-approval of a material obligation without a real human gate — barred
            if quorum > 1:
                continue  # opener never counts toward a multi-party quorum (Slice 2.2, Ch 5 doctrine)
        # Slice 2.1 (cross-mandate blocking, S2-V4 Ch 2 mandate separation): a material obligation
        # scoped to a mandate is approved only if the acting principal HOLDS that mandate (recorded on
        # the approval). Composed with AH-1, independent of it — a real gate at mandate A cannot mint
        # authority over mandate B. Unscoped obligations pass through (guard returns True).
        if material and not _mguard.approval_holds_mandate(debit, e):
            continue  # cross-mandate act on a material obligation without holding its mandate — barred
        # Wave W1 (witness ceremony, S2-V4 Ch 2 §221-227): a witness-BACKED cross-mandate auth must
        # validate structurally against the chain (the xm_witness entry with matching anchors must
        # exist) — fail-closed. A bare declared auth (no witness_ref) keeps the 2.1 floor unchanged.
        xm = e.get("cross_mandate_auth")
        if material and isinstance(xm, dict) and "witness_ref" in xm \
                and not _witness.validate_witness_ref(entries, xm["witness_ref"]):
            continue  # witness-backed auth whose witness is absent/mismatched on-chain — barred
        approvers.add(e.get("approved_by"))
        if len(approvers) >= quorum:
            return True
    return False


def replay(entries: list[dict]) -> dict:
    """Reconstruct state from the append-only chain (order-aware reopen handling)."""
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
    # Mirrors is_approved EXACTLY (Slice 2.2 tightening of the audit fix): the display view derives
    # approved from the same guarded read as enforcement — a quorum-pending obligation (1 of N
    # reviewers in) must not DISPLAY approved while the gate reads pending (display-vs-enforce class).
    approved = {oid for oid in debits if is_approved(entries, oid)}
    for oid in approved:
        if oid in debits:
            debits[oid] = {**debits[oid], "draft": False, "approved": True}
    open_obs = [d for oid, d in debits.items() if oid not in closed]
    closed_obs = [d for oid, d in debits.items() if oid in closed]
    return {"open": open_obs, "closed": closed_obs, "all": list(debits.values())}


def attestation_status(entries: list[dict], obligation_id: str, required: set) -> dict:
    """Replay attestations + vetoes for an obligation (ORDER-AWARE: the last veto/clear per role
    governs). Default-deny: any standing veto ⇒ vetoed=True ⇒ cannot execute. `required` is the
    obligation's requires_attestation set (resolved by the caller)."""
    required = set(required or [])
    attested, veto_state = set(), {}   # role -> 'veto'/'clear' (last wins, in chain order)
    veto_reasons = {}
    for e in entries:
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


def full_log(entries: list[dict]) -> list[dict]:
    """Per-obligation materialized record incl. approval + close evidence/receipt. Newest first."""
    obs = {e["id"]: dict(e) for e in entries if e.get("type") == "debit"}
    for e in entries:
        t = e.get("type")
        if t == "approval" and e.get("approves") in obs:
            d = obs[e["approves"]]
            d["disposition"] = e.get("disposition", "approved")
            # Mirrors is_approved exactly (audit fix + Slice 2.2): denied/pending AND quorum-pending
            # must not read as approved on the display surface (display-vs-enforce class).
            d["approved"] = is_approved(entries, e["approves"])
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


def recompute_chain(entries: list[dict], chain_corrupt: bool) -> bool:
    """Full hash-walk from genesis — the O(n) ground truth behind the memoized verify_chain.
    `chain_corrupt` is the gateway's middle-hole flag (a committed hole ⇒ invalid regardless of links)."""
    # A corrupt MIDDLE line is a hole in the committed chain (Universalize Wave §1/G2): the gateway
    # already dropped it and flagged chain_corrupt — the chain is NOT valid regardless of the surviving
    # links. A truncated trailing line (repair_required without chain_corrupt) is an interrupted append,
    # not a committed hole, so the clean prefix can still verify.
    if chain_corrupt:
        return False
    prev = "genesis"
    for e in entries:
        if e.get("prev_hash") != prev:
            return False
        if e.get("hash") != _hash({k: v for k, v in e.items() if k != "hash"}):
            return False
        prev = e["hash"]
    return True


def refs(entries: list[dict], type: str = "debit") -> set:
    """The set of non-empty `ref` strings for entries of the given chain type (default 'debit')."""
    return {e.get("ref") for e in entries if e.get("type") == type and e.get("ref")}


def open_obligations(replay_result: dict, owner=None) -> list[dict]:
    obs = replay_result["open"]
    return [o for o in obs if o["owner"] == owner] if owner else obs


def by_status(replay_result: dict) -> dict:
    return {"open": len(replay_result["open"]), "closed": len(replay_result["closed"]),
            "total": len(replay_result["all"])}


def by_owner(replay_result: dict) -> dict:
    """Per-owner open/closed counts derived from the ORDER-AWARE replay (reopen-aware open/closed sets)."""
    open_ids = {o["id"] for o in replay_result["open"]}
    out: dict[str, dict] = {}
    for o in replay_result["all"]:
        bucket = out.setdefault(o["owner"], {"open": 0, "closed": 0})
        bucket["open" if o["id"] in open_ids else "closed"] += 1
    return out


def manifest(entries: list[dict], file_path: str, by_status_counts: dict, chain_valid: bool) -> dict:
    """One-glance proof of ledger state (P0-1): last_hash + counts + chain_valid for the agent's chain."""
    last = entries[-1] if entries else None
    return {
        "file": file_path,
        "chain_entries": len(entries),
        "obligations": by_status_counts,
        "chain_valid": chain_valid,
        "last_hash": last.get("hash") if last else None,
        "last_prev_hash": last.get("prev_hash") if last else None,
        "last_ts": last.get("timestamp") if last else None,
        "last_type": last.get("type") if last else None,
        "last_ref": (last.get("title") or last.get("closes") or last.get("approves") or "—") if last else None,
    }
