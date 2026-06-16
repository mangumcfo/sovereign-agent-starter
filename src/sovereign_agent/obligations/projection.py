"""Pure projection functions over an obligation-chain `entries` list — extracted verbatim from the
ObligationLedger read methods (audit 2026-06-16 #6, extraction not abstraction).

These are STATELESS and deterministic: same entries -> same output. All memoization stays on the
ObligationLedger instance (the class methods are thin wrappers that call these inside their caches), so
caching behavior is byte-identical. No imports from ledger.py (no cycle); only _util for the chain hash.
"""
from __future__ import annotations

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
    return any(e.get("type") == "approval" and e.get("approves") == obligation_id
               and e.get("disposition", "approved") == "approved"
               for e in entries)


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
    # Only approvals actually DISPOSITIONED 'approved' count (audit fix): a denied/pending
    # approval entry must not flip a draft to approved in the replay view. Mirrors is_approved.
    approved = {e["approves"] for e in entries
                if e.get("type") == "approval" and e.get("disposition", "approved") == "approved"}
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
