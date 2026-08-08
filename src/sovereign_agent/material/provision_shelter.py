# -*- coding: utf-8 -*-
"""material.provision_shelter — Shelter & Manufacturing (Series 9, Vol 4).

`provision_shelter` provisions a **built structure** — a dwelling or manufactured shelter, at a location,
with a capacity and a condition — as a receipted, mandate-scoped governed object. It composes the sealed
**Material Primitive** (S9 Vol 1, `provision_local` / `verify_provision`) and adds exactly the shelter
domain: a required location, an honest capacity (non-negative), and a condition drawn from a known set, so
a structure is a governed object a successor can prove is theirs and inheritable.

Kill-targets: **no central housing authority** (each node provisions its own structures into its OWN local
registry — inherited from V01) · **human primacy** over the physical act (a gated provision is refused
without a human approval — inherited from V01) · **verify by receipt, not a registry** (`verify_shelter`
confirms a structure — that it is theirs, under one mandate, in the stated condition — from its receipt
alone, via V01's `verify_provision`; a receiver or heir reads a green light with no second device) ·
**honest condition** (a capacity cannot be negative; a condition must be a known value) · **rolls no
cryptography** (composes V01; adds none). The structure's economic value homes OUT to Sovereign Economy
(S10); the material estate — the inheritance of the dwelling itself — homes to Generational Transfer (S12).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .provision_local import (            # The Material Primitive (S9 Vol 1) — composed by identity
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
)

__all__ = ["provision_shelter", "verify_shelter", "shelter_good", "CONDITIONS",
           "ProvisionRefused", "ProvisionStatus"]

CONDITIONS = ("habitable", "needs-repair", "uninhabitable")


def shelter_good(dwelling: str, *, location: str, capacity: Any, condition: str,
                 unit: str = "persons") -> dict:
    """The canonical shelter good: a structure at a location, with a capacity and a condition. Identity is
    keyed on dwelling + location so a structure at a place is ONE governed object."""
    if not str(dwelling).strip():
        raise ProvisionRefused("shelter provision requires a named dwelling")
    if not str(location).strip():
        raise ProvisionRefused("shelter provision requires a location")
    if str(condition) not in CONDITIONS:
        raise ProvisionRefused(f"shelter condition must be one of {CONDITIONS} — got {condition!r}")
    try:
        cap = float(capacity)
    except (TypeError, ValueError):
        raise ProvisionRefused("shelter capacity must be a number")
    if cap < 0:
        raise ProvisionRefused("shelter capacity cannot be negative")
    return {"id": f"shelter:{dwelling}@{location}", "dwelling": str(dwelling), "location": str(location),
            "capacity": cap, "unit": str(unit), "condition": str(condition)}


def provision_shelter(dwelling: str, *, location: str, capacity: Any, condition: str, mandate: str,
                      author: str, source_ref: str, at: str, registry: Any, unit: str = "persons",
                      approver: Optional[str] = None, approval_ref: Optional[str] = None, gate: Any = None,
                      action_class: str = "provision_shelter",
                      role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Provision a built structure as a receipted, mandate-scoped governed object into the node's LOCAL
    registry, and return its receipt. Composes `provision_local` (S9 Vol 1): no central housing authority,
    human-primacy-gated, verifiable by receipt. Honest: location required, capacity non-negative, condition
    from a known set."""
    good = shelter_good(dwelling, location=location, capacity=capacity, condition=condition, unit=unit)
    return provision_local(good, mandate=mandate, author=author, source_ref=source_ref, at=at,
                           registry=registry, approver=approver, approval_ref=approval_ref, gate=gate,
                           action_class=action_class, role_spec=role_spec, mode=mode)


def verify_shelter(receipt: Mapping[str, Any], dwelling: str, *, location: str, capacity: Any,
                   condition: str, unit: str = "persons") -> ProvisionStatus:
    """Weakest-party check: confirm a structure — that it is theirs (one mandate), at the stated location,
    in the stated condition — from its receipt alone, with no registry, no second device, no expertise. A
    tampered condition, capacity, or location flips the green light. Composes V01's `verify_provision`."""
    good = shelter_good(dwelling, location=location, capacity=capacity, condition=condition, unit=unit)
    return verify_provision(receipt, good)
