"""_sealed_host_seam — the ONE thin adapter for every crypto call site in the yield organism.

the node's sealed-host convention (2026-07-08, §3): the sealed crypto substrate
(`breathline_primitives`, shipped as a sealed tarball — real ed25519/secp256k1 sign+verify) is ABSENT in
every dev environment (this cloud AND the dev box). It installs from the sealed distribution on the
"sealed host"; that install is the node's wiring step.

So every crypto call in the yield organism routes through THIS module, and every stub returns an EXPLICIT
sentinel — `SEALED_HOST_PENDING` / `UNVERIFIED` — never a fake `True`. A fabricated pass here would be a
constitutional lie (the whole point of the receipted organism is that verification is real or it is absent,
never pretended). When the node unpacks the sealed tarball, he wires the real primitives behind these two
functions and nothing else in the yield organism changes — the pure, crypto-free logic already stands alone.

This module has NO dependency on breathline_primitives at import time (it must import in a crypto-free env);
the real engine is bound only inside the seam functions, at wiring time.
"""
from __future__ import annotations

from typing import Optional

# ── Explicit sentinels — an absent verification is NAMED, never a silent/fake True. ──
SEALED_HOST_PENDING = "SEALED_HOST_PENDING"   # the crypto engine is not wired in this env
UNVERIFIED = "UNVERIFIED"                     # a signature/bundle was not (could not be) verified here

# States a caller may treat as "not a real cryptographic assurance" — fail-safe set.
NOT_ASSURED = frozenset({SEALED_HOST_PENDING, UNVERIFIED})


def is_verified(status: str) -> bool:
    """True ONLY for an explicit real-verified status. Every sentinel is False (fail-safe)."""
    return status == "VERIFIED"


def sign_value_flow(record: dict, *, signer: Optional[str] = None) -> dict:
    """SEALED-HOST-SEAM: crypto-engine ring — sign the value-flow record — stubbed (returns
    SEALED_HOST_PENDING); the node wires bl-sign on the sealed host against the sealed primitives.

    Returns the record annotated with an EXPLICIT pending sentinel — never a fabricated signature.
    """
    return {**record, "signature": None, "signature_status": SEALED_HOST_PENDING}


def verify_economic_bundle(bundle: dict) -> str:
    """SEALED-HOST-SEAM: crypto-engine ring — bl-verify the economic bundle / cross-node attestation —
    stubbed (returns UNVERIFIED); the node wires bl-verify on the sealed host.

    Returns an EXPLICIT sentinel, never a fake `True`. Callers must treat UNVERIFIED as not-assured.
    """
    return UNVERIFIED
