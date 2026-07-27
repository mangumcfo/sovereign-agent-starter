"""identity.py — stable object identity + version records (S5-05-E2-2).

Every object version carries authorship and a resolvable source reference. The
provenance law is the existing R22-3 validator (obligations.provenance), reused
verbatim: a path-like source_ref must resolve or the version is refused — a
citation is never written false. Canonical bytes + hashing come from
evidence.export_packet so the whole object model shares one byte convention.
"""
from __future__ import annotations

from ..evidence.export_packet import _canon, _sha
from ..obligations.provenance import _assert_source_ref_resolves


class VersionRefused(ValueError):
    """A version that would be dishonest (no author, unresolvable source) is refused."""


def object_id(cls_: str, natural_key: str) -> str:
    """Stable identity: class + natural key. Never derived from storage position."""
    if not cls_ or not natural_key:
        raise VersionRefused("object identity requires a class and a natural key")
    return f"{cls_}:{natural_key}"


def make_version(obj_id: str, seq: int, payload: dict, *, author: str,
                 source_ref: str, at: str, kind: str = "change",
                 approver: str | None = None, approval_ref: str | None = None,
                 prev_hash: str | None = None) -> dict:
    """Build one immutable version record. Refuses without an author or with an
    unresolvable source_ref (R22-3). `at` is a caller-stated ISO date/time — the
    model never reads a clock. The version_hash covers every field, so any later
    byte change is detectable."""
    if not str(author).strip():
        raise VersionRefused(f"version for {obj_id} refused: author is required")
    if not str(source_ref).strip():
        raise VersionRefused(f"version for {obj_id} refused: source_ref is required")
    _assert_source_ref_resolves(source_ref)  # raises on a false citation
    v = {"object_id": obj_id, "seq": int(seq), "kind": kind, "at": str(at),
         "payload": payload, "author": author, "source_ref": source_ref,
         "approver": approver, "approval_ref": approval_ref,
         "prev_hash": prev_hash}
    v["version_hash"] = _sha(_canon(v))
    return v


def version_leaf(version: dict) -> str:
    """The leaf hash a version contributes to any root: identity + content, canonical."""
    return _sha(_canon({"object_id": version["object_id"],
                        "version_hash": version["version_hash"]}))
