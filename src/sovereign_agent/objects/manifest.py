"""manifest.py — manifests as constitutional snapshots (S5-05-E3-1, E3-3).

A manifest is cut over the registry at a stated time and verifies by recomputing
its root from the object list — omit one object and the root moves. Period-end
manifests are retained permanently and chained to their predecessors (each carries
its prior period's root and a hash over its own fields).
"""
from __future__ import annotations

from ..evidence.export_packet import _canon, _merkle_root, _sha
from .registry import ObjectRegistry, root_from_object_list


def cut_manifest(reg: ObjectRegistry, *, at: str, period_end: bool = False,
                 prior_manifest: dict | None = None) -> dict:
    """Cut a manifest over the registry's current population at a stated time."""
    state = reg.current()
    m = {"at": str(at), "count": len(state),
         "root": _merkle_root(reg.population_leaves(state)),
         "period_end": bool(period_end),
         "prior_root": (prior_manifest or {}).get("root"),
         "prior_manifest_hash": (prior_manifest or {}).get("manifest_hash")}
    m["manifest_hash"] = _sha(_canon(m))
    return m


def verify_manifest(manifest: dict, object_list: list[dict]) -> tuple[bool, str]:
    """An outsider's check: recompute the root from the bare object list and
    compare. Returns (ok, recomputed_root). Any omission or byte change moves
    the recomputed root off the manifest's (E3-1)."""
    recomputed = root_from_object_list(object_list)
    return recomputed == manifest["root"] and len(
        {v["object_id"] for v in object_list}) == manifest["count"], recomputed


def verify_chain(manifests: list[dict]) -> tuple[bool, str | None]:
    """Period-end manifests chain: each must cite its predecessor's root and
    manifest_hash, and each manifest_hash must recompute (E3-3).
    Returns (ok, first_break_description)."""
    prev = None
    for m in manifests:
        body = {k: m[k] for k in ("at", "count", "root", "period_end",
                                  "prior_root", "prior_manifest_hash")}
        if _sha(_canon(body)) != m["manifest_hash"]:
            return False, f"manifest at {m['at']}: manifest_hash does not recompute"
        if prev is not None and (m["prior_root"] != prev["root"] or
                                 m["prior_manifest_hash"] != prev["manifest_hash"]):
            return False, f"manifest at {m['at']}: does not chain to predecessor at {prev['at']}"
        prev = m
    return True, None
