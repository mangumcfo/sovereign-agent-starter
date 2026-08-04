"""Entities — the governed multi-entity structure: a registry of legal entities, their ownership graph, and the
consolidation hierarchy that control implies.

Co-extrusion for s5_18 (Multi-Entity & Consolidation, KM wave-V18 2026-08-04). Pure / structural, no crypto substrate
(runs in a pure public clone, no skip -- F-1 posture). An entity carries its reporting currency and is owned some
percentage by a parent entity; an entity a parent controls (ownership > 50%) consolidates into that parent's group.
The registry is validated fail-closed: every parent defined, every ownership percentage in [0, 100], every entity a
currency, and no cycle in the ownership graph. The group under a root is then a derived fact -- root plus everything it
reaches by a chain of control -- not a list someone maintains by hand."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping, Set, Union

Number = Union[int, float, str, Decimal]

CONTROL_THRESHOLD = Decimal("50")  # ownership strictly greater than 50% = control = consolidate


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class EntityError(ValueError):
    """Raised for an undefined parent, an ownership percentage outside [0, 100], a missing currency, or a cycle."""


def validate_structure(entities: Mapping[str, Mapping]) -> None:
    """Fail-closed validation of an entity registry. Each entry maps an entity id to a mapping with:
    `parent` (another entity id, or None for a top parent), `ownership_pct` (the percent of THIS entity owned by its
    parent, in [0, 100]), and `currency` (its reporting currency). Refuses an undefined parent, an out-of-range
    percentage, a missing currency, or a cycle in the ownership graph."""
    if not entities:
        raise EntityError("empty entity registry")
    for eid, e in entities.items():
        parent = e.get("parent")
        if parent is not None and parent not in entities:
            raise EntityError(f"entity {eid!r} names parent {parent!r} not in the registry")
        pct = _dec(e.get("ownership_pct", 0))
        if not (Decimal("0") <= pct <= Decimal("100")):
            raise EntityError(f"entity {eid!r} ownership_pct {pct} is outside [0, 100]")
        if not e.get("currency"):
            raise EntityError(f"entity {eid!r} has no reporting currency")
    for eid in entities:
        seen: Set[str] = set()
        cur = eid
        while cur is not None:
            if cur in seen:
                raise EntityError(f"ownership cycle through entity {eid!r}")
            seen.add(cur)
            cur = entities[cur].get("parent")


def group_members(entities: Mapping[str, Mapping], root: str) -> Set[str]:
    """The set of entities consolidated into the group under `root`: root itself plus every entity reached by a chain
    of control (ownership > 50% at each step). An entity owned 50% or less is not controlled and does not consolidate
    (it is an investment, not a subsidiary). Assumes a validated registry."""
    if root not in entities:
        raise EntityError(f"root {root!r} not in the registry")
    members = {root}
    frontier = [root]
    while frontier:
        p = frontier.pop()
        for cid, e in entities.items():
            if cid not in members and e.get("parent") == p and _dec(e.get("ownership_pct", 0)) > CONTROL_THRESHOLD:
                members.add(cid)
                frontier.append(cid)
    return members


def effective_ownership(entities: Mapping[str, Mapping], root: str, entity: str) -> Decimal:
    """The group's effective economic ownership of `entity` — the product of the ownership fractions along the chain
    of control from `root` down to `entity` (root itself is 1). Used for minority-interest reasoning; a fully
    controlled subsidiary consolidates in full with an elimination, while this fraction records the economic share."""
    if entity == root:
        return Decimal("1")
    chain = []
    cur = entity
    while cur is not None and cur != root:
        chain.append(cur)
        cur = entities[cur].get("parent")
    if cur != root:
        raise EntityError(f"entity {entity!r} is not under root {root!r}")
    eff = Decimal("1")
    for c in chain:
        eff *= _dec(entities[c].get("ownership_pct", 0)) / Decimal("100")
    return eff
