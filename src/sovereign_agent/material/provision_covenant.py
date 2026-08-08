# -*- coding: utf-8 -*-
"""material.provision_covenant — The Provision Covenant (Series 9, Vol 6, the CAPSTONE).

`provision_covenant` is the single governed covenant a node provisions ALL matter under. It **composes**
the five sealed material provisioners — the Material Primitive (V01, a generic good), Sovereign Energy
(V02), Regenerative Food & Water (V03), Shelter & Manufacturing (V04), and Logistics & Supply (V05) —
into one covenant surface, and it **re-implements none of them**. Every kind is provisioned by dispatching
to its own sealed provisioner; every good is verified by the one uniform check the whole series shares
(`verify_provision`), because all five provisioners compose it. So a node provisions energy, sustenance,
shelter, movement, or any good under one covenant, and any receiver verifies any of them the same way.

Kill-targets: **composes, never re-implements** (the covenant imports the five sealed provisioners; it
rolls no provisioning, no hashing, no registry write of its own) · **one covenant over all kinds** (a
single declared set of provision kinds; an unknown kind is refused, deny-by-default) · **no central
provisioner** (each dispatch writes to the node's OWN registry — inherited from every provisioner) ·
**human primacy** (a gated provision under the covenant is refused without a human approval — inherited) ·
**weakest-party verifiable** (`verify_under_covenant` is one uniform green light for a good of ANY kind,
no registry, no second device, no expertise) · **rolls no cryptography** (composes the sealed floors'
hashing; adds none). All economic value homes OUT to Sovereign Economy (S10); all material estate to
Generational Transfer (S12). On this volume's seal, Material Sovereignty (Series 9) closes at 6/6.
"""
from __future__ import annotations

from typing import Any, Mapping, Tuple

from .provision_local import (            # V01 The Material Primitive — the shared verify + a generic good
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
)
from .provision_energy import provision_energy            # V02 Sovereign Energy
from .provision_sustenance import provision_sustenance    # V03 Regenerative Food & Water
from .provision_shelter import provision_shelter          # V04 Shelter & Manufacturing
from .provision_shipment import provision_shipment        # V05 Logistics & Supply

__all__ = ["provision_kinds", "provision_under_covenant", "verify_under_covenant",
           "PROVISION_COVENANT", "ProvisionRefused", "ProvisionStatus"]

# The covenant: the declared set of material provision kinds, each bound to its own SEALED provisioner.
# Composition, not re-implementation — every value is another volume's sealed function.
PROVISION_COVENANT = {
    "good": provision_local,          # S9 Vol 1
    "energy": provision_energy,       # S9 Vol 2
    "sustenance": provision_sustenance,  # S9 Vol 3
    "shelter": provision_shelter,     # S9 Vol 4
    "shipment": provision_shipment,   # S9 Vol 5
}


def provision_kinds() -> Tuple[str, ...]:
    """The covenant's declared provision kinds, sorted — the inspectable set of what a node may provision
    under this covenant (the five sealed material volumes)."""
    return tuple(sorted(PROVISION_COVENANT))


def provision_under_covenant(kind: str, *args: Any, **kwargs: Any) -> dict:
    """Provision a good of `kind` by DISPATCHING to its own sealed provisioner — composing V01–V05, never
    re-implementing them. An unknown kind is refused (deny-by-default). Returns the provisioner's receipt.
    Locality, human primacy, honest domain guards, and tamper-evidence are each the composed volume's."""
    if kind not in PROVISION_COVENANT:
        raise ProvisionRefused(
            f"provision kind {kind!r} is not in the covenant {provision_kinds()} — deny-by-default")
    return PROVISION_COVENANT[kind](*args, **kwargs)


def verify_under_covenant(receipt: Mapping[str, Any], good: Mapping[str, Any]) -> ProvisionStatus:
    """Verify a good of ANY kind under the covenant, uniformly — the one weakest-party green light the
    whole series shares. Because every provisioner (V01–V05) composes `verify_provision`, verifying a good
    against its receipt is the same check for energy, sustenance, shelter, a movement, or any good: it
    re-derives the receipt from its own fields and confirms the good, with no registry, no second device,
    and no expertise. A tamper to the good or the receipt flips the light. Rolls no cryptography."""
    return verify_provision(receipt, good)
