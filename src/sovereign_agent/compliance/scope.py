"""Scope — a jurisdiction or standard scope as a first-class object: which standards and which report packs apply,
selectable one at a time or across several (multi-jurisdiction), fail-closed on an unknown scope or member.

Co-extrusion for s5_14 (Compliance & Audit + Reporting, KM Option B+ 2026-08-03). Pure / structural, no crypto substrate
(runs in a pure public clone, no skip — F-1 posture). A real organization is bound by different standards and reporting
requirements in different jurisdictions; a scope makes that binding a governed object rather than tribal knowledge -- it
names the standards and packs that apply, and selecting by scope returns exactly those, refusing a scope or a member the
registry does not define. Multi-jurisdiction selection is the union across several scopes. The libraries of ready-made
jurisdiction scopes deepen within this volume; the scoping mechanism runs today."""
from __future__ import annotations

from typing import Dict, List, Mapping


class ScopeError(ValueError):
    """Raised for an unknown scope id, or a scope that names a standard or pack the registry does not define."""


def make_scope(scope_id: str, name: str, standards: List[str], packs: List[str]) -> Dict[str, object]:
    """Define a scope: an id, a human name, the standard names it requires, and the report-pack names it requires.
    A scope with no standards and no packs is refused -- an empty scope binds nothing and is a definition error."""
    if not scope_id or not name:
        raise ScopeError("a scope needs an id and a name")
    if not standards and not packs:
        raise ScopeError(f"scope {scope_id!r} binds no standards and no packs")
    return {"id": scope_id, "name": name, "standards": list(standards), "packs": list(packs)}


def select_for_scope(scope: Mapping, standards_registry: Mapping, packs_registry: Mapping) -> Dict[str, object]:
    """Return the standards and packs a scope selects, resolved from the registries. Fail-closed: a standard or pack
    the scope names but the registry does not define is refused, so a scope can never silently select nothing where it
    claimed to bind something."""
    sel_standards = {}
    for s in scope["standards"]:
        if s not in standards_registry:
            raise ScopeError(f"scope {scope['id']!r} names unknown standard {s!r}")
        sel_standards[s] = standards_registry[s]
    sel_packs = {}
    for p in scope["packs"]:
        if p not in packs_registry:
            raise ScopeError(f"scope {scope['id']!r} names unknown pack {p!r}")
        sel_packs[p] = packs_registry[p]
    return {"scope": scope["id"], "standards": sel_standards, "packs": sel_packs}


def select_for_scopes(scope_ids: List[str], scope_registry: Mapping,
                      standards_registry: Mapping, packs_registry: Mapping) -> Dict[str, object]:
    """Multi-jurisdiction selection: the union of standards and packs across several scopes. An unknown scope id is
    refused. The result names which scopes contributed, so a multi-jurisdiction obligation is itself a governed set."""
    if not scope_ids:
        raise ScopeError("no scopes selected")
    standards: Dict[str, object] = {}
    packs: Dict[str, object] = {}
    for sid in scope_ids:
        if sid not in scope_registry:
            raise ScopeError(f"unknown scope {sid!r}")
        sel = select_for_scope(scope_registry[sid], standards_registry, packs_registry)
        standards.update(sel["standards"])
        packs.update(sel["packs"])
    return {"scopes": list(scope_ids), "standards": standards, "packs": packs}
