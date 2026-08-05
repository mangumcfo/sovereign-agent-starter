"""Distributed Manufacturing (s5_39 / reading Vol 41) — the federated bill of materials as a governed, forkable object.

A bill of materials that no single entity owns: **versioned, forkable, receipted**, its assembly identity a manifest
root over the governed parts. Centralized production is a chokepoint and a black box; a federated BOM is a governed
object any node can verify and fork under the blueprint's own governance.

It builds **one new act -- a BOM as a governed object with a forkable lineage and a manifest-root assembly identity**
-- by composing the sealed Sovereign Object Model (its registry and manifest), not by building a BOM store, a merkle
engine, or a marketplace of its own:

  * `open_bom` -- register a BOM as a governed object under one mandate (composing the sealed object registry): its
    parts are an authored, provenance-checked payload; an empty id or empty parts is refused.
  * `fork_bom` -- fork a BOM into a NEW governed object that cites its parent and the parent's exact version
    (composing the registry): a forkable lineage on the record, the parent version never touched.
  * `bom_root` -- the **assembly identity**: the sealed manifest root over the registry's governed BOM objects
    (composing `objects.manifest.cut_manifest` -- a pure-hashlib merkle root, not a new engine). The root changes
    when the governed parts change, so a receiver can verify what they assembled from the root alone.

No BOM store, no merkle engine, no marketplace -- only the federated-BOM governance over the sealed object model. The
node capability declaration, ZK-pooled order matching, and mesh optimization are the surfaces this composes toward,
homed at their series (Federation Node Governance Vol 28; the marketplace and Zero-Trust/ZK series); not built here.
Pure composition (the object model is hashlib-based): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.manifest import cut_manifest


class BOMError(ValueError):
    """Raised when a federated BOM cannot be opened or forked honestly: an empty id or empty parts, or a fork of a
    BOM that does not exist. Fail-closed -- a bill of materials is a governed object with real content and a real
    parent, or it is not registered."""


def open_bom(reg, bom_id: str, parts: Mapping, *, mandate: str, author: str,
             source_ref: str, at: str) -> Dict[str, object]:
    """Open a bill of materials as a governed object under a mandate -- composing the sealed object registry. Its
    `parts` become the object's payload, authored and provenance-checked, registered under exactly one mandate. The
    BOM is now a governed object like any other: versioned, integrity-hashed, and owned by one mandate -- not a file
    a single entity controls. An empty `bom_id` or empty `parts` is refused."""
    if not bom_id:
        raise BOMError("a bill of materials needs an id")
    if not parts:
        raise BOMError("a bill of materials needs at least one part")
    obj_id = f"bom:{bom_id}"
    return reg.append(obj_id, {"parts": dict(parts)}, author=author, source_ref=source_ref, at=at,
                      mandate=mandate, kind="ratify")


def fork_bom(reg, bom_id: str, *, new_id: str, author: str, source_ref: str, at: str,
             mandate: str = None) -> Dict[str, object]:
    """Fork a BOM into a NEW governed object that cites its parent -- composing the registry. The fork copies the
    parent's current parts and records the parent id and the parent's exact `version_hash`, so the lineage is on the
    record and a fork can always be traced to what it forked from. The parent version is never touched. A fork of a
    BOM that does not exist, or with an empty `new_id`, is refused. The fork is registered under the same mandate as
    its parent unless a new `mandate` is given (a node taking the blueprint under its own mandate)."""
    if not new_id:
        raise BOMError("a fork needs a new id")
    parent = reg.current().get(f"bom:{bom_id}")
    if parent is None:
        raise BOMError(f"cannot fork {bom_id!r}: no such bill of materials")
    payload = {
        "parts": dict((parent.get("payload") or {}).get("parts") or {}),
        "forked_from": bom_id,
        "forked_at_version": parent.get("version_hash"),
    }
    obj_id = f"bom:{new_id}"
    return reg.append(obj_id, payload, author=author, source_ref=source_ref, at=at,
                      mandate=(mandate or parent.get("mandate")), kind="ratify")


def bom_root(reg, *, at: str) -> str:
    """The assembly identity for the federated production state -- the sealed manifest root over the registry's
    governed BOM objects (composing `objects.manifest.cut_manifest`, a pure-hashlib merkle root). The root is a
    fingerprint of the governed parts: it changes when the parts change, so a receiver can verify what they were
    handed from the root alone, without trusting the sender. This composes the object model's manifest; it computes
    no root of its own."""
    return cut_manifest(reg, at=at)["root"]
