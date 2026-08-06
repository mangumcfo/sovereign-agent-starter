"""Distributed sovereign compute — a node offers governed capacity; a job is admitted only by the node's declared consent.

Co-extrusion for s6_03 (Distributed Sovereign Compute, KM S6 GO 2026-08-05). Pure / structural, no crypto substrate
beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). Sovereign nodes contribute compute to
shared work WITHOUT a central scheduler and WITHOUT any hub that seizes a node's compute: each node registers a governed
offer of the capacity it makes available, and a job is admitted to run on that capacity only when the node's offer
covers it AND the node has DECLARED a crossing that admits the requester. No scheduler commands a node's compute; a job
runs on a node only by the node's own governed offer and its own declared consent.

Two governed acts:
  * `offer_capacity` registers a node's compute-capacity offer as a governed, provenance-carrying object -- composing the
    sealed object registry (`reg.append`, kind=ratify): the units the node makes available are authored under the node's
    mandate, carrying its `author`, `source_ref` (provenance), and a `version_hash` (integrity). An empty node id or a
    non-positive capacity is refused. The offer is the node's own governed statement of what it will contribute -- not a
    quota a scheduler assigns.
  * `admit_job` admits a compute job to a node's offered capacity DENY-BY-DEFAULT, fail-closed, IN ORDER: the offer must
    be a real governed offer; the job's requested units must not exceed the offered capacity (no over-subscription -- a
    node's compute is never seized beyond what it offered); admission must be authorized by a peer-declared crossing on
    the offer (composing the sealed cross-mandate access check `node_gov.authorize_crossing` -- the node consents by
    declaring the rule, and own-mandate use is whole); and the requester must be named. Only then is the job admitted,
    returning the admission and the node's remaining capacity. No central scheduler admits a job -- the node does, by its
    offer and its declared consent.

Human primacy and the sovereignty boundary hold: a node's compute is its own governed offer, and a job runs on it only
by the node's declared consent, never a scheduler's command. This module builds no scheduler, no job queue, no
orchestrator, and no compute broker of its own -- the offer is the sealed object model's governed object, and the
consent is the sealed cross-mandate scope check, composed."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping, Sequence, Union

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..federation.node_gov import authorize_crossing
from ..objects.scope import ScopeRefusal

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ComputeError(ValueError):
    """Raised when compute cannot be offered or admitted honestly: an offer with no node id or non-positive capacity, a
    job that would exceed the node's offered capacity, or an admission with no declared crossing or no named requester --
    fail-closed, a node's compute is its own governed offer admitted only by its declared consent, never seized by a
    scheduler."""


def offer_capacity(reg, node_id: str, units: Number, *, mandate: str, author: str,
                   source_ref: str, at: str) -> Dict[str, object]:
    """Register a node's compute-capacity offer as a governed, provenance-carrying object under one mandate -- composing
    the sealed object registry. The `units` the node makes available become the object's authored payload, carrying the
    node's `author`, `source_ref` (provenance), and a `version_hash` (integrity). An empty `node_id` or non-positive
    `units` is refused. The offer is the node's own governed statement of the compute it will contribute -- not a quota a
    scheduler assigns. Returns the governed offer object."""
    if not node_id:
        raise ComputeError("a capacity offer needs a node id")
    u = _dec(units)
    if u <= 0:
        raise ComputeError(f"a capacity offer needs positive units (got {u})")
    return reg.append(f"capacity:{node_id}", {"units": str(u)}, author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="ratify")


def admit_job(reg, rules: Sequence, offer: Mapping, job_units: Number, *, requester_mandate: str,
              want: str = "write") -> Dict[str, object]:
    """Admit a compute job to a node's offered capacity -- DENY-BY-DEFAULT, fail-closed, on conditions IN ORDER:

      1. the `offer` must be a real governed capacity offer -- carrying a `version_hash` (its integrity) and an object
         id; an admission against no governed offer is refused;
      2. the job's `job_units` must not exceed the offered capacity -- a job larger than the node offered is refused (no
         over-subscription: a node's compute is never seized beyond what it offered);
      3. admission must be authorized by a PEER-DECLARED crossing on the offer -- composing the sealed cross-mandate
         access check (`node_gov.authorize_crossing`): own-mandate use is whole, a cross-mandate requester is admitted
         only via a `SharingRule` naming exactly this offer, this requester, and a scope at least as strong; an
         undeclared admission is refused (the node consents by declaring the rule -- no central scheduler admits it);
      4. the requester must be named -- an empty requester mandate is refused.

    Only when the offer is real AND the capacity covers the job AND the node has declared the crossing AND the requester
    is named is the job admitted, returning the admission and the node's remaining capacity. No central scheduler admits
    a job; the node does, by its own offer and its own declared consent."""
    if not str(requester_mandate).strip():
        raise ComputeError("admission refused: a named requester is required (no anonymous compute admission)")
    if not (offer and offer.get("version_hash") and offer.get("object_id")):
        raise ComputeError("admission refused: no real governed capacity offer to admit against")
    offered = _dec((offer.get("payload") or {}).get("units", 0))
    req = _dec(job_units)
    if req <= 0:
        raise ComputeError(f"a job needs positive units (got {req})")
    if req > offered:
        raise ComputeError(
            f"admission refused: job of {req} units exceeds the node's offered capacity of {offered} "
            f"-- a node's compute is never seized beyond what it offered (no over-subscription)"
        )
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=requester_mandate,
                                obj_id=offer["object_id"], want=want)
    except ScopeRefusal as e:
        raise ComputeError(
            f"admission refused: no declared crossing admits {requester_mandate!r} to run on the offer "
            f"{offer['object_id']!r} -- a node's compute is admitted only by its declared consent, never seized ({e})"
        )
    if not ok:
        raise ComputeError("admission refused: the node has not consented to admit this requester")
    return {"admitted": True, "node": offer["object_id"], "units": str(req),
            "remaining": str(offered - req), "requester": requester_mandate}
