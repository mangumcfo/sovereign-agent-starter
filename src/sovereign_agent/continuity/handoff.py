"""Generational Continuity (s5_27 / reading Vol 29) — the governed generational handoff.

A business meant to last is handed on -- to an heir, a successor generation, a new steward -- and the handoff is
where continuity is won or lost. The legacy handoff is a transfer of trust: the outgoing operator vouches for the
records, and the successor inherits a system they must take on faith, its truth walking out the door with the person
who kept it. This module refuses that. It makes a handoff a transfer of *proof*: a successor receives a package that
verifies itself, handed over only through a human gate.

It builds **one new act -- governing a generational handoff, fail-closed** -- by composing the sealed Sovereign
Object Model and the human-gate convention, not by building a successor-packet engine of its own:

  * `assemble_successor_package` -- the verifiable business package for heirs: composes the sealed `cut_manifest` +
    `build_packet` (Sovereign Object Model) into a self-verifying successor packet, which a successor validates from
    its own bytes on a machine holding none of the operator's systems.
  * `govern_handoff` -- the handoff is **fail-closed**: the successor package must VERIFY (composing the sealed
    `verify_packet`) AND the handoff must be approved by a NAMED human (an approver + a resolvable approval
    reference, the object model's own human-gate convention). A package that does not verify, or a handoff with no
    human approval, is refused -- a business is not handed on on faith, and not without a human's assent.

No successor-packet engine, no second object model -- only the handoff governance over the sealed floors. Pure
composition (the object model is hashlib-based, no crypto substrate): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping

from ..objects.manifest import cut_manifest
from ..objects.inheritance import build_packet, verify_packet


class HandoffError(ValueError):
    """Raised when a generational handoff cannot proceed honestly: a successor package that does not verify, or a
    handoff with no named human approver / no resolvable approval reference. Fail-closed -- a business is handed on
    as proof through a human gate, or it is not handed on."""


def assemble_successor_package(reg, *, at: str) -> Dict[str, object]:
    """Assemble the verifiable business package for heirs -- composing the sealed object model's manifest and
    successor packet (`cut_manifest` -> `build_packet`). The package is SELF-VERIFYING: a successor validates it
    from its own bytes, on a machine holding none of the operator's systems. This module assembles the package; the
    packet machinery and its integrity are the object model's, not reimplemented here."""
    manifest = cut_manifest(reg, at=at)
    return build_packet(reg, manifest)


def govern_handoff(package: Mapping, *, approver: str, approval_ref: str) -> Dict[str, object]:
    """Govern a generational handoff -- FAIL-CLOSED on two conditions, in order:

      1. the successor package must VERIFY -- composing the sealed `verify_packet`, a pure check over the package's
         own bytes; a package that does not verify (a tampered or malformed successor packet) refuses the handoff;
      2. the handoff must be approved by a NAMED human -- an `approver` and a resolvable `approval_ref` (the object
         model's own human-gate convention, the same approver + approval reference a governed change carries); a
         handoff with no named approver or no approval reference is refused.

    Only when the package verifies AND a human has approved does the handoff complete, returning a receipted result
    (the package root, the approver, the approval reference). The verification is the object model's; the human
    approval is the operator's; the handoff adds only the fail-closed binding -- proof AND a human, or no handoff."""
    ok, fails = verify_packet(dict(package))
    if not ok:
        raise HandoffError(
            "generational handoff refused: the successor package does not verify -- " + "; ".join(fails)
            + " -- a business is handed on as proof, not on faith"
        )
    if not str(approver).strip():
        raise HandoffError("generational handoff refused: a named human approver is required (no silent handoff)")
    if not str(approval_ref).strip():
        raise HandoffError("generational handoff refused: a resolvable approval reference is required")
    return {
        "handed_off": True,
        "package_root": (package.get("manifest") or {}).get("root"),
        "approver": approver,
        "approval_ref": approval_ref,
        "verified": True,
    }
