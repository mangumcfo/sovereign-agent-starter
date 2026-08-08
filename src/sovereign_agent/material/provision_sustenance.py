# -*- coding: utf-8 -*-
"""material.provision_sustenance — Regenerative Food & Water (Series 9, Vol 3).

`provision_sustenance` provisions a **food or water good** — a quantity, of a kind, from a traceable
origin — as a receipted, mandate-scoped governed object. It composes the sealed **Material Primitive**
(S9 Vol 1, `provision_local` / `verify_provision`) and adds exactly the sustenance domain: a required,
traceable **origin** (regenerative provenance — where the food or water came from) and an honest quantity,
so a receiver can confirm not only that a good is sovereignly provisioned but where it came from.

Kill-targets: **no central provisioner** (each node provisions its own sustenance into its OWN local
registry — inherited from V01) · **human primacy** over the physical act (a gated provision is refused
without a human approval — inherited from V01) · **verify by receipt, not a registry** (`verify_sustenance`
confirms a good and its origin from the receipt alone, via V01's `verify_provision` — weakest-party green
light) · **origin never absent or false** (a food/water good requires a traceable origin, and V01's
provenance rule keeps its source citation honest) · **honest quantity** (a negative/absent quantity is
refused) · **rolls no cryptography** (composes V01; adds none). The good's economic value homes OUT to
Sovereign Economy (S10); the material estate to Generational Transfer (S12).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .provision_local import (            # The Material Primitive (S9 Vol 1) — composed by identity
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
)

__all__ = ["provision_sustenance", "verify_sustenance", "sustenance_good",
           "ProvisionRefused", "ProvisionStatus"]

_KINDS = ("food", "water")


def sustenance_good(item: str, quantity: Any, *, kind_of: str, origin: str, unit: str = "kg") -> dict:
    """The canonical sustenance good: a quantity of a food/water item from a traceable origin. Identity is
    keyed on kind + item + origin so provenance is part of the good's identity."""
    if str(kind_of) not in _KINDS:
        raise ProvisionRefused(f"sustenance kind must be one of {_KINDS} — got {kind_of!r}")
    if not str(item).strip():
        raise ProvisionRefused("sustenance provision requires a named item")
    if not str(origin).strip():
        raise ProvisionRefused("sustenance requires a traceable origin — regenerative provenance is not optional")
    try:
        amount = float(quantity)
    except (TypeError, ValueError):
        raise ProvisionRefused("sustenance quantity must be a number")
    if amount < 0:
        raise ProvisionRefused("sustenance quantity cannot be negative")
    return {"id": f"{kind_of}:{item}:{origin}", "item": str(item), "kind_of": str(kind_of),
            "quantity": amount, "unit": str(unit), "origin": str(origin)}


def provision_sustenance(item: str, quantity: Any, *, kind_of: str, origin: str, mandate: str, author: str,
                         source_ref: str, at: str, registry: Any, unit: str = "kg",
                         approver: Optional[str] = None, approval_ref: Optional[str] = None, gate: Any = None,
                         action_class: str = "provision_sustenance",
                         role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Provision a food or water good, with a traceable origin, as a receipted, mandate-scoped governed
    object into the node's LOCAL registry, and return its receipt. Composes `provision_local` (S9 Vol 1):
    no central provisioner, human-primacy-gated, verifiable by receipt; origin is required."""
    good = sustenance_good(item, quantity, kind_of=kind_of, origin=origin, unit=unit)
    return provision_local(good, mandate=mandate, author=author, source_ref=source_ref, at=at,
                           registry=registry, approver=approver, approval_ref=approval_ref, gate=gate,
                           action_class=action_class, role_spec=role_spec, mode=mode)


def verify_sustenance(receipt: Mapping[str, Any], item: str, quantity: Any, *, kind_of: str, origin: str,
                      unit: str = "kg") -> ProvisionStatus:
    """Weakest-party check: confirm a food/water good AND its origin from the receipt alone — no registry,
    no second device, no expertise. A tampered item, quantity, or origin flips the green light. Composes
    V01's `verify_provision` over the canonical sustenance good."""
    good = sustenance_good(item, quantity, kind_of=kind_of, origin=origin, unit=unit)
    return verify_provision(receipt, good)
