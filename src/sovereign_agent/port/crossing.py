"""The Sovereign Port — a governed boundary crossing between the sovereign core and the outside world.

Co-extrusion for s6_07 (The Sovereign Port, KM S6 residual 2026-08-06, MUST-SOLO). Pure / structural, no crypto
substrate beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). The sovereign core reaches the
outside world -- an external rail, a bank, a market feed, a regulator, a legacy system -- only across a governed
boundary: the crossing is the node's OWN sanctioned, receipted act, not a hub's. The Port does not settle, hold, or move
value; it does not own the crossing. It governs one thing: that every reach outside is a declared, authorized,
human-sanctioned, receipted boundary act -- and it records that the crossing happened, never the value itself.

Two governed acts:
  * `open_crossing` registers a crossing as a governed, provenance-carrying object under the node's OWN mandate --
    composing the sealed object registry (`reg.append` kind=ratify): a crossing names an external `target` (the rail /
    system / authority reached) and carries an `instruction` (WHAT crosses -- a reference or directive, never value
    itself), authored, carrying author/source/integrity. The crossing is the node's own governed statement of intent to
    reach outside, not a hub's queue entry. An empty node id, target, or instruction is refused.
  * `sanction_crossing` sanctions a crossing DENY-BY-DEFAULT, fail-closed, in order: the crossing must be a real
    governed object (carrying a `version_hash`); the crossing must be AUTHORIZED by a node-DECLARED boundary rule
    (composing the sealed `node_gov.authorize_crossing` -- the node declares a `SharingRule` naming exactly this crossing
    and the boundary it may reach; an undeclared crossing is refused, so no central authority sanctions it -- the node
    does, by its own declared consent); and a NAMED human must approve (composing the sealed `HumanApprovalGate` --
    reaching outside the sovereign boundary is high-materiality, so a named approver + a non-empty approval reference are
    required). Only then is the crossing sanctioned, returning a governed RECEIPT that the crossing occurred -- never the
    value. No central settlement authority sanctions a crossing, no value is held or moved, and no hub owns it.

Human primacy and the sovereignty boundary hold: the crossing is the node's own governed object, its authorization is
the node's own declared rule, and its sanction is a named human's assent. This module builds no settlement engine, no
value custody, no payment rail, and no connectivity hub of its own -- the byte-carriage / wire and the external rail
itself are the node's own runtime and the outside world, homed OUT (designed-toward); delivery BETWEEN nodes is the
sealed Receipted Inter-Node Messaging. The Port governs the crossing; it does not open the socket, and it never touches
the money."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..objects.scope import ScopeRefusal
from ..federation.node_gov import authorize_crossing
from ..compliance.human_approval_gate import HumanApprovalGate


class CrossingError(ValueError):
    """Raised when a boundary crossing cannot be sanctioned honestly: a crossing with no node id, target, or
    instruction, or a sanction of no real governed crossing, of an undeclared boundary, or with no named human --
    fail-closed, the sovereign core reaches outside only by its own governed, declared, human-sanctioned, receipted
    crossing, never a central settlement authority's or a hub's."""


def open_crossing(reg, node_id: str, target: str, instruction: Mapping, *, mandate: str, author: str,
                  source_ref: str, at: str) -> Dict[str, object]:
    """Open a boundary crossing as a governed object under the node's OWN mandate -- composing the sealed object registry
    (`reg.append` kind=ratify). The crossing names an external `target` (the rail / system / authority reached) and
    carries an `instruction` (WHAT crosses -- a reference or directive, never value), authored and provenance-carrying,
    so the node's intent to reach outside is on the record. An empty `node_id`, `target`, or `instruction` is refused.
    Returns the governed crossing object. The Port holds no value -- the instruction is a directive, not funds."""
    if not node_id:
        raise CrossingError("a crossing needs the node id that is reaching outside")
    if not target:
        raise CrossingError("a crossing needs a target -- the external rail / system / authority it reaches")
    if not instruction:
        raise CrossingError("a crossing needs an instruction -- WHAT crosses (a directive/reference, never value)")
    return reg.append(f"crossing:{node_id}:{target}", dict(instruction), author=author,
                      source_ref=source_ref, at=at, mandate=mandate, kind="ratify")


def sanction_crossing(reg, crossing: Mapping, *, rules: Sequence, boundary_mandate: str, approver: str,
                      approval_ref: str, gate: HumanApprovalGate = None) -> Dict[str, object]:
    """Sanction a boundary crossing -- DENY-BY-DEFAULT, fail-closed, in order:

      1. the `crossing` must be a real governed object -- carrying a `version_hash` (its integrity) and an object id; a
         sanction of nothing, or of an ungoverned crossing, is refused;
      2. the crossing must be AUTHORIZED by a node-DECLARED boundary rule -- composing the sealed
         `node_gov.authorize_crossing`: the node declares a `SharingRule` naming exactly this crossing object and the
         `boundary_mandate` it may reach, with a scope at least as strong; an undeclared crossing is refused (no central
         authority sanctions the reach outside -- the node does, by its own declared consent);
      3. a NAMED human must approve -- composing the sealed `HumanApprovalGate` (reaching outside the sovereign boundary
         is high-materiality): an `approver` and a non-empty `approval_ref` naming the sanction; a crossing with no named
         approver or no reference is refused (no value-bearing reach outside without a named human's assent).

    Only when the crossing is a real governed object AND the node has declared the boundary AND a human has approved is
    the crossing sanctioned, returning a governed RECEIPT that the crossing occurred (its root, boundary, and the named
    human) -- never the value itself. No central settlement authority sanctions a crossing, no value is held or moved,
    and no hub owns it -- the Port records that a sanctioned crossing happened, and nothing more."""
    if not (crossing and crossing.get("version_hash") and crossing.get("object_id")):
        raise CrossingError("crossing refused: no real governed crossing to sanction")
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=boundary_mandate,
                                obj_id=crossing["object_id"], want="write")
    except ScopeRefusal as e:
        raise CrossingError(
            f"crossing refused: no declared boundary rule authorizes reaching {boundary_mandate!r} with the crossing "
            f"{crossing['object_id']!r} -- the core reaches outside only by its own declared consent, never a hub ({e})"
        )
    if not ok:
        raise CrossingError("crossing refused: the node has not declared this boundary crossing (deny-by-default)")
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["boundary_crossing"]})
    if not gate.requires_approval(
        "boundary_crossing",
        {"charter_v7_forbidden_classes": ["boundary_crossing"]},
        "corporate_regulated",
    ):
        raise CrossingError("crossing refused: reaching outside must be a human-gated action class (deny-by-default)")
    if not str(approver).strip():
        raise CrossingError("crossing refused: a named human approver is required (no silent reach outside)")
    if not str(approval_ref).strip():
        raise CrossingError("crossing refused: an approval reference naming the sanction is required")
    return {"crossed": True, "crossing_root": crossing.get("version_hash"),
            "boundary": boundary_mandate, "object_id": crossing.get("object_id"),
            "approver": approver, "approval_ref": approval_ref}
