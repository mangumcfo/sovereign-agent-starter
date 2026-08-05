"""Sovereign collaboration — nodes co-govern shared work without a central collaboration server.

Co-extrusion for s6_02 (Sovereign Collaboration, KM S6 Marketplace-style wave 2026-08-05). Pure / structural, no crypto
substrate beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). Two or more sovereign nodes
collaborate on a shared work object WITHOUT a central collaboration server: each contribution is a governed,
provenance-carrying version the other node validates for itself, and a peer participates only because a sharing rule was
DECLARED for it -- deny-by-default, no central grant authority.

Two governed acts:
  * `contribute` records a node's contribution to a shared collaboration as a governed, provenance-carrying version --
    composing the sealed object registry (`reg.append`): the contribution carries its `author`, its `source_ref`
    (provenance), and a `version_hash` (integrity), and the collaboration object is scoped to exactly one home mandate;
    an empty collaboration id or empty contribution is refused. Each contribution is a receipt, so the collaboration is
    a chain of governed contributions no server owns.
  * `authorize_participation` gates a peer's participation DENY-BY-DEFAULT -- composing the sealed cross-mandate access
    check (`node_gov.authorize_crossing` -> `objects.scope.check_access`): a peer may participate only via a
    peer-declared `SharingRule` naming exactly this collaboration, this peer mandate, and a scope at least as strong; a
    crossing exists ONLY because a rule was declared for it, never because a server let the peer in. Own-mandate
    participation is whole; an undeclared cross-mandate participation is refused (`ScopeRefusal`).

Human primacy and the sovereignty boundary hold: the contribution is the contributing node's governed object, and a
peer's participation is a peer-declared crossing, not a central grant. This module builds no collaboration server, no
shared workspace store, and no access-control engine of its own -- the governed contribution is the sealed object
model's, and the peer-declared crossing is the sealed cross-mandate scope check's, composed."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..federation.node_gov import authorize_crossing
from ..objects.scope import ScopeRefusal


class CollaborationError(ValueError):
    """Raised when a collaboration cannot proceed honestly: a contribution with no id or no body, or a peer's
    participation that no declared sharing rule grants -- fail-closed, a collaboration is a chain of governed
    contributions a peer validates for itself, and participation is a peer-declared crossing, never a central grant."""


def contribute(reg, collaboration_id: str, contribution: Mapping, *, mandate: str, author: str,
               source_ref: str, at: str) -> Dict[str, object]:
    """Record a node's contribution to a shared collaboration as a governed, provenance-carrying version -- composing
    the sealed object registry. The `contribution` becomes an authored version of the collaboration object, carrying the
    contributing node's `author`, its `source_ref` (provenance), and a `version_hash` (integrity); the collaboration is
    scoped to exactly one home mandate (the registry enforces one-mandate-per-object). An empty `collaboration_id` or
    empty `contribution` is refused. Returns the governed contribution version."""
    if not collaboration_id:
        raise CollaborationError("a collaboration needs an id")
    if not contribution:
        raise CollaborationError("a contribution needs a body")
    return reg.append(f"collab:{collaboration_id}", dict(contribution), author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="change")


def authorize_participation(reg, rules: Sequence, collaboration_id: str, *, peer_mandate: str,
                            want: str = "read") -> bool:
    """Gate a peer's participation in a collaboration DENY-BY-DEFAULT -- composing the sealed cross-mandate access check
    (`node_gov.authorize_crossing`). Own-mandate participation is whole; a cross-mandate peer may participate only via a
    peer-declared `SharingRule` naming exactly this collaboration object, this peer mandate, and a scope at least as
    strong as `want`. A participation that no declared rule grants is refused (there is no central grant authority: a
    crossing exists only because a peer declared the rule for it). Returns True when the participation is authorized."""
    obj_id = f"collab:{collaboration_id}"
    try:
        return authorize_crossing(reg, list(rules), principal_mandate=peer_mandate, obj_id=obj_id, want=want)
    except ScopeRefusal as e:
        raise CollaborationError(
            f"participation refused: no declared sharing rule grants {peer_mandate!r} {want!r} on the collaboration "
            f"{collaboration_id!r} -- a crossing exists only by a peer-declared rule, never a central grant ({e})"
        )
