# -*- coding: utf-8 -*-
"""material.provision_energy — Sovereign Energy (Series 9, Vol 2).

`provision_energy` provisions a **metered energy quantity** — a generation or a stored amount, over a
stated period, from a named asset — as a receipted, mandate-scoped governed object. It composes the sealed
**Material Primitive** (S9 Vol 1, `provision_local` / `verify_provision`) and adds exactly the energy
domain: an honest meter (a reading is non-negative and unit-typed) and a period-scoped identity, so a
generation period is one governed object with one receipt.

Kill-targets: **no central utility** (each node meters and provisions its own energy into its OWN local
registry — inherited from V01's no-central-provisioner) · **human primacy** over the physical energy act
(a gated provision is refused without a human approval — inherited from V01) · **verify by receipt, not a
utility registry** (`verify_energy` confirms a metered amount from its receipt alone, via V01's
`verify_provision` — weakest-party green light, no second device) · **honest metering** (a negative or
absent reading is refused) · **rolls no cryptography** (composes V01, which composes the Object Model's
hashing; it adds none). The energy's economic value homes OUT to Sovereign Economy (S10); the material
estate to Generational Transfer (S12).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .provision_local import (            # The Material Primitive (S9 Vol 1) — composed by identity
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
)

__all__ = ["provision_energy", "verify_energy", "energy_good", "ProvisionRefused", "ProvisionStatus"]


def energy_good(asset: str, kwh: Any, *, period: str, unit: str = "kWh") -> dict:
    """The canonical energy good: a metered quantity from an asset over a period. Identity is keyed on
    asset + period so a generation period is ONE governed object (not double-counted)."""
    if not str(asset).strip():
        raise ProvisionRefused("energy provision requires a named asset")
    if not str(period).strip():
        raise ProvisionRefused("energy provision requires a stated period")
    try:
        amount = float(kwh)
    except (TypeError, ValueError):
        raise ProvisionRefused("energy meter reading must be a number")
    if amount < 0:
        raise ProvisionRefused("energy meter reading cannot be negative — honest metering refuses it")
    return {"id": f"{asset}@{period}", "asset": str(asset), "kwh": amount,
            "unit": str(unit), "period": str(period)}


def provision_energy(asset: str, kwh: Any, *, period: str, mandate: str, author: str, source_ref: str,
                     at: str, registry: Any, unit: str = "kWh", approver: Optional[str] = None,
                     approval_ref: Optional[str] = None, gate: Any = None,
                     action_class: str = "provision_energy",
                     role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Provision a metered energy quantity as a receipted, mandate-scoped governed object into the node's
    LOCAL registry, and return its receipt. Composes `provision_local` (S9 Vol 1): no central utility,
    human-primacy-gated, verifiable by receipt. Honest metering: a negative/absent reading is refused."""
    good = energy_good(asset, kwh, period=period, unit=unit)
    return provision_local(good, mandate=mandate, author=author, source_ref=source_ref, at=at,
                           registry=registry, approver=approver, approval_ref=approval_ref, gate=gate,
                           action_class=action_class, role_spec=role_spec, mode=mode)


def verify_energy(receipt: Mapping[str, Any], asset: str, kwh: Any, *, period: str,
                  unit: str = "kWh") -> ProvisionStatus:
    """Weakest-party check: confirm a metered energy amount from its receipt alone — no utility registry,
    no second device, no expertise. A tampered reading, asset, or period flips the green light. Composes
    V01's `verify_provision` over the canonical energy good."""
    good = energy_good(asset, kwh, period=period, unit=unit)
    return verify_provision(receipt, good)
