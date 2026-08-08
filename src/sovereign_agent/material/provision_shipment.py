# -*- coding: utf-8 -*-
"""material.provision_shipment — Logistics & Supply (Series 9, Vol 5).

`provision_shipment` provisions a **logistics movement** — a good moving from an origin to a destination,
by a carrier, in a quantity — as a receipted, mandate-scoped governed object. It composes the sealed
**Material Primitive** (S9 Vol 1, `provision_local` / `verify_provision`) and adds exactly the logistics
domain: a required origin and destination (which must differ), a named carrier, and an honest quantity, so
a shipment's chain of custody is a governed object a receiver can prove — with no central dispatcher.

Kill-targets: **no central dispatcher** (each node provisions its own movements into its OWN local registry
— inherited from V01; no shared broker or carrier registry) · **human primacy** over the physical act (a
gated provision is refused without a human approval — inherited from V01) · **verify by receipt, not a
registry** (`verify_shipment` confirms a movement — its origin, destination, carrier, and custody — from
its receipt alone, via V01's `verify_provision`; a receiver reads a green light with no dispatcher) ·
**honest custody** (origin and destination are required and must differ; a quantity cannot be negative) ·
**rolls no cryptography** (composes V01; adds none). The moved good's economic value homes OUT to Sovereign
Economy (S10); the material estate to Generational Transfer (S12).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .provision_local import (            # The Material Primitive (S9 Vol 1) — composed by identity
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
)

__all__ = ["provision_shipment", "verify_shipment", "shipment_good",
           "ProvisionRefused", "ProvisionStatus"]


def shipment_good(good_ref: str, *, origin: str, destination: str, carrier: str, quantity: Any,
                  unit: str = "units") -> dict:
    """The canonical shipment good: a movement of a good from an origin to a destination by a carrier.
    Identity is keyed on good_ref + origin + destination so a movement is ONE governed object and its
    origin and destination are part of what it IS."""
    if not str(good_ref).strip():
        raise ProvisionRefused("shipment provision requires a good reference")
    if not str(origin).strip():
        raise ProvisionRefused("shipment provision requires an origin")
    if not str(destination).strip():
        raise ProvisionRefused("shipment provision requires a destination")
    if str(origin) == str(destination):
        raise ProvisionRefused("shipment origin and destination must differ — a movement goes somewhere")
    if not str(carrier).strip():
        raise ProvisionRefused("shipment provision requires a named carrier")
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ProvisionRefused("shipment quantity must be a number")
    if qty < 0:
        raise ProvisionRefused("shipment quantity cannot be negative")
    return {"id": f"shipment:{good_ref}:{origin}->{destination}", "good_ref": str(good_ref),
            "origin": str(origin), "destination": str(destination), "carrier": str(carrier),
            "quantity": qty, "unit": str(unit)}


def provision_shipment(good_ref: str, *, origin: str, destination: str, carrier: str, quantity: Any,
                       mandate: str, author: str, source_ref: str, at: str, registry: Any,
                       unit: str = "units", approver: Optional[str] = None,
                       approval_ref: Optional[str] = None, gate: Any = None,
                       action_class: str = "provision_shipment",
                       role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Provision a logistics movement as a receipted, mandate-scoped governed object into the node's LOCAL
    registry, and return its receipt. Composes `provision_local` (S9 Vol 1): no central dispatcher,
    human-primacy-gated, verifiable by receipt. Honest custody: origin and destination required and
    distinct, carrier named, quantity non-negative."""
    good = shipment_good(good_ref, origin=origin, destination=destination, carrier=carrier,
                         quantity=quantity, unit=unit)
    return provision_local(good, mandate=mandate, author=author, source_ref=source_ref, at=at,
                           registry=registry, approver=approver, approval_ref=approval_ref, gate=gate,
                           action_class=action_class, role_spec=role_spec, mode=mode)


def verify_shipment(receipt: Mapping[str, Any], good_ref: str, *, origin: str, destination: str,
                    carrier: str, quantity: Any, unit: str = "units") -> ProvisionStatus:
    """Weakest-party check: confirm a movement — its origin, destination, carrier, and quantity — from its
    receipt alone, with no dispatcher, no second device, no expertise. A tampered origin, destination,
    carrier, or quantity flips the green light. Composes V01's `verify_provision`."""
    good = shipment_good(good_ref, origin=origin, destination=destination, carrier=carrier,
                         quantity=quantity, unit=unit)
    return verify_provision(receipt, good)
