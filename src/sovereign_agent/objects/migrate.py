"""migrate.py — cutover honesty (S5-05-E7-1, E7-3).

Migrated objects are stamped `origin: asserted` at cutover. An object with a
signed attestation naming a source document is `sourced`; one without stays
`unsourced` PERMANENTLY — and an unsourced object can never be promoted to
sealed. Attestations are counted and must reconcile against the migrated
population: sourced + unsourced = total, or the cutover is refused.
"""
from __future__ import annotations


class SealRefused(PermissionError):
    """An unsourced object cannot be promoted to sealed — no paper, no seal."""


class ReconciliationError(ValueError):
    """sourced + unsourced must equal the migrated population, exactly."""


def stamp_cutover(objects: list[dict], attestations: dict[str, str]) -> list[dict]:
    """Stamp every migrated object `origin: asserted`; mark sourced/unsourced from
    the attestation map (object_id -> source document ref). Returns new dicts —
    the input records are never mutated (append-only discipline even in memory)."""
    stamped = []
    for o in objects:
        s = dict(o)
        s["origin"] = "asserted"
        ref = attestations.get(s["object_id"])
        if ref:
            s["sourced"] = True
            s["cutover_attestation"] = ref
        else:
            s["sourced"] = False
            s["unsourced"] = True  # permanent, travels in every export (E8-4)
        stamped.append(s)
    return stamped


def promote_to_sealed(obj: dict) -> dict:
    """Sealing is reserved for sourced objects. Unsourced refuses loudly (E7-1)."""
    if not obj.get("sourced"):
        raise SealRefused(
            f"{obj.get('object_id')}: unsourced object cannot be promoted to sealed — "
            "it stays visibly unsourced; sealing requires a cutover attestation "
            "naming a source document")
    out = dict(obj)
    out["sealed"] = True
    return out


def reconcile(stamped: list[dict]) -> dict:
    """Count and reconcile: sourced + unsourced = population, exactly (E7-3)."""
    sourced = sum(1 for o in stamped if o.get("sourced"))
    unsourced = sum(1 for o in stamped if o.get("unsourced"))
    pop = len(stamped)
    if sourced + unsourced != pop:
        raise ReconciliationError(
            f"cutover does not reconcile: {sourced} sourced + {unsourced} unsourced "
            f"!= {pop} migrated")
    return {"population": pop, "sourced": sourced, "unsourced": unsourced,
            "reconciles": True}
