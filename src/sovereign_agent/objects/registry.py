"""registry.py — the sovereign object registry (S5-05-E2-1, S5-05-E6-1 storage half).

A registry holds every business object under a stable identity and derives ONE
integrity root over the whole population. Storage is an append-only NDJSON of
version records (the obligations-ledger discipline at object granularity): state
is derived by replay, never asserted by a current-value row. The population root
is deterministic — recomputable byte-identical from the object list alone.
"""
from __future__ import annotations

import json
import os

from ..evidence.export_packet import _merkle_root
from ..ndjson import read_ndjson
from .identity import VersionRefused, make_version, version_leaf


class MandateViolation(ValueError):
    """An object belongs to exactly one mandate — a second registration refuses."""


class ObjectRegistry:
    """Append-only registry. One file, one population, one root."""

    def __init__(self, root_dir: str):
        os.makedirs(root_dir, exist_ok=True)
        self.path = os.path.join(root_dir, "objects.ndjson")
        if not os.path.exists(self.path):
            open(self.path, "w").close()

    # ── replay (state is derived, never asserted) ──────────────────────────
    def entries(self) -> list[dict]:
        r = read_ndjson(self.path)  # the ONE chain-read parser (Universalize §1)
        if r.chain_corrupt:
            raise RuntimeError(
                f"object registry {self.path} has a corrupt middle line "
                f"({r.bad_line}) — degrade loudly, repair before replay")
        return r.entries

    def versions(self, obj_id: str) -> list[dict]:
        return [e for e in self.entries() if e["object_id"] == obj_id]

    def current(self) -> dict[str, dict]:
        """object_id -> latest version, by replay in append order."""
        state: dict[str, dict] = {}
        for e in self.entries():
            state[e["object_id"]] = e
        return state

    def mandate_of(self, obj_id: str) -> str | None:
        vs = self.versions(obj_id)
        return vs[0].get("mandate") if vs else None

    # ── append ─────────────────────────────────────────────────────────────
    def append(self, obj_id: str, payload: dict, *, author: str, source_ref: str,
               at: str, mandate: str, kind: str = "change",
               approver: str | None = None, approval_ref: str | None = None) -> dict:
        """Append one version. First version registers the object under exactly one
        mandate; later versions must not move it (S5-05-E6-1)."""
        prior = self.versions(obj_id)
        if prior and prior[0].get("mandate") != mandate:
            raise MandateViolation(
                f"{obj_id} is scoped to mandate {prior[0].get('mandate')!r}; "
                f"registration under {mandate!r} refused — an object belongs to "
                "exactly one mandate")
        if not mandate:
            raise VersionRefused(f"{obj_id}: a mandate is required at registration")
        v = make_version(obj_id, len(prior) + 1, payload, author=author,
                         source_ref=source_ref, at=at, kind=kind, approver=approver,
                         approval_ref=approval_ref,
                         prev_hash=prior[-1]["version_hash"] if prior else None)
        v["mandate"] = mandate
        with open(self.path, "a") as f:
            f.write(json.dumps(v, sort_keys=True) + "\n")
        return v

    # ── the one root ───────────────────────────────────────────────────────
    def population_leaves(self, state: dict[str, dict] | None = None) -> list[str]:
        """Ordered leaf hashes over the CURRENT population, sorted by object_id —
        deterministic from the object list alone."""
        state = self.current() if state is None else state
        return [version_leaf(state[k]) for k in sorted(state)]

    def population_root(self) -> str:
        return _merkle_root(self.population_leaves())


def root_from_object_list(versions: list[dict]) -> str:
    """Recompute the population root from a bare object list (no registry, no
    store) — the byte-identical recompute S5-05-E2-1 promises an outsider."""
    state = {v["object_id"]: v for v in sorted(versions, key=lambda v: (v["object_id"], v["seq"]))}
    return _merkle_root([version_leaf(state[k]) for k in sorted(state)])
