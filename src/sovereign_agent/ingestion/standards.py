"""Multi-Standard Ingestion (s5_25 / reading Vol 27) — map external standards into sovereign-typed intake.

An enterprise is met by many external standards: EDI trade documents, ISO payment messages, a regulatory board's
reporting schema, a partner's data format. Each must come *into* the sovereign system as governed, typed objects —
and the recurring failure is a bespoke importer per standard, each with its own idea of the target shape, drifting
from the others and from the objects the enterprise actually keeps. Worse, when an external standard changes, a
silent importer maps the new field into the old shape (or drops it), and the drift is discovered only in an audit.

This module refuses that. It builds **one new act — mapping an external-standard record into a sovereign-typed
object version, drift-safe** — and it builds it by *composing the sealed Sovereign Object Model*, not by standing up
a second master-data system:

  * `map_record` applies a **declared** field mapping (external field -> sovereign field) and is **drift-safe,
    fail-closed**: a source field that is neither mapped nor explicitly dropped is REFUSED (an external-standard
    change that adds a field cannot silently corrupt intake), and two source fields mapping to one sovereign field
    with different values is a refused collision. Value-conserving: each mapped value crosses unchanged.
  * `ingest_record` turns the mapped payload into a sealed **object version** via `objects.identity.make_version`
    (Sovereign Object Model) — authored, provenance-stamped (make_version refuses a missing author, and a
    path-like source_ref that does not resolve; a symbolic standard citation is recorded as stated, not verified
    against the standard), immutable, version-hashed. The identity, authorship, and integrity are the object
    model's; this module adds only the mapping.
  * `ingest_standard` ingests a batch and anchors it to a **provenance root** (`objects.proofs.tree_root` over the
    version leaves) as receipted ingestion evidence — fail-closed: if *any* record drifts or lacks a natural key,
    the whole batch is refused (a partial ingest is a drifted ingest).

No second master-data system, no per-standard importer sprawl — only the drift-safe mapping over the sealed object
model. Pure composition (the object model is hashlib-based, no crypto substrate): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from ..objects.identity import object_id, make_version, version_leaf
from ..objects.proofs import tree_root


class IngestionError(ValueError):
    """Raised when an external-standard record cannot be mapped honestly: an unmapped (undropped) source field
    (mapping drift), a mapping collision, or a mapped record with no natural key. Fail-closed — a record that would
    drift the intake is refused, not coerced."""


def map_record(external: Mapping, mapping: Mapping, *, drop: Sequence[str] = ()) -> Dict[str, object]:
    """Map ONE external-standard record into a sovereign-typed payload via a DECLARED field mapping
    (`{external_field: sovereign_field}`). Drift-safe, fail-closed:

      * a source field that is neither in the mapping nor in `drop` is REFUSED — an external standard that adds a
        field cannot silently corrupt intake; the mapping must be updated (or the field dropped) deliberately;
      * two source fields mapping to the SAME sovereign field with DIFFERENT values is a refused collision (an
        undeclared conflict between two parts of the standard);
      * value-conserving — each mapped field's value crosses unchanged.

    The mapping is the whole governance surface: what the standard's fields become in the sovereign type is declared,
    not inferred, so a reader (or an auditor) can see exactly how each external field lands."""
    drop_set = set(drop)
    payload: Dict[str, object] = {}
    src_of: Dict[str, str] = {}
    for k, v in external.items():
        if k in drop_set:
            continue
        if k not in mapping:
            raise IngestionError(
                f"unmapped source field {k!r} -- declare it in the mapping or drop it explicitly "
                "(mapping drift refused, fail-closed)"
            )
        tgt = mapping[k]
        if tgt in payload and payload[tgt] != v:
            raise IngestionError(
                f"mapping collision on sovereign field {tgt!r}: {k!r} and {src_of[tgt]!r} map to it with "
                "different values -- resolve the conflict in the declared mapping"
            )
        payload[tgt] = v
        src_of[tgt] = k
    return payload


def ingest_record(
    external: Mapping,
    mapping: Mapping,
    *,
    cls_: str,
    natural_key_field: str,
    author: str,
    source_ref: str,
    at: str,
    seq: int = 1,
    drop: Sequence[str] = (),
) -> Dict[str, object]:
    """Map an external-standard record into a sealed sovereign OBJECT VERSION -- composing the Sovereign Object
    Model (`object_id` + `make_version`). The mapped payload becomes an authored, provenance-stamped, immutable,
    version-hashed object version: `make_version` refuses a missing author, and a path-like source_ref that does
    not resolve (the provenance law); a symbolic standard citation (e.g. an EDI/ISO profile name) is recorded as
    stated, not verified against the standard. So an ingested record carries who ingested it and which standard it
    cites, with honest authorship and tamper-evident integrity -- not a proof the cited standard is genuine. The
    sovereign identity is `cls_` + the record's natural key (from the mapped payload). No second master-data system:
    identity, authorship, provenance, and integrity are all the object model's."""
    payload = map_record(external, mapping, drop=drop)
    nk = payload.get(natural_key_field)
    if nk is None or str(nk).strip() == "":
        raise IngestionError(
            f"mapped record has no natural key ({natural_key_field!r}) -- a sovereign identity cannot be formed "
            "without one"
        )
    oid = object_id(cls_, str(nk))
    return make_version(oid, seq, payload, author=author, source_ref=source_ref, at=at, kind="ingest")


def ingest_standard(
    records: Sequence[Mapping],
    mapping: Mapping,
    *,
    cls_: str,
    natural_key_field: str,
    author: str,
    source_ref: str,
    at: str,
    drop: Sequence[str] = (),
) -> Dict[str, object]:
    """Ingest a BATCH of external-standard records into sovereign-typed object versions and anchor the batch to a
    provenance root -- receipted ingestion evidence. Composes the sealed object model's identity/versions and its
    merkle proofs (`tree_root` over the version leaves). Fail-closed: if ANY record drifts (an unmapped field, a
    collision, or no natural key), the whole batch is refused -- a partial ingest is a drifted ingest, and an
    ingestion you cannot fully account for is not evidence. Returns the versions, the count, and the
    `ingestion_root` (the fingerprint of exactly these records, in exactly these mappings)."""
    versions: List[Dict[str, object]] = [
        ingest_record(r, mapping, cls_=cls_, natural_key_field=natural_key_field,
                      author=author, source_ref=source_ref, at=at, seq=1, drop=drop)
        for r in records
    ]
    root = tree_root([version_leaf(v) for v in versions])
    return {"versions": versions, "count": len(versions), "ingestion_root": root}
