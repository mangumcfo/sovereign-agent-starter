# -*- coding: utf-8 -*-
"""sovereign_ux.verify_surface — Zero-Trust UX (S8 Vol 7).

`verify_surface` renders a read-only surface of what has been **VERIFIED**, not what is merely
**VOUCHED**. It reads the verdicts the sealed zero-trust floors produce — Shields (S7 Vol 2) and Verified
Flows (S7 Vol 4, `attest_flow_clears`) — and renders them through the Sovereign Lens (V01) so that:

  * a **cleared proof** from a named sealed floor reads as **verified**;
  * a **failed proof** reads as **failed** — never hidden;
  * an **absent, malformed, or merely-vouched** claim (asserted with no proof) reads as **unverified** —
    never as passing (**fail-closed / adversarial clarity**: the surface trusts nothing it cannot prove).

Kill-targets: **shows what verified, never what is vouched** · **no second verification authority** —
it runs no check of its own; it renders the floors' verdicts (imports no shield/flow/evidence engine) ·
**adversarial clarity** — a failed or absent proof reads as failed, never silently passing. The in-tree
`evidence` module is rendered **READ-ONLY** (`evidence_view`), never composed as a sealed floor. **Rolls
no cryptography** — the verification is the sealed floors'; this surface only displays their verdicts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .lens import render_view, View                      # V01 The Sovereign Lens

__all__ = ["VerifyStatus", "verify_surface", "is_verified", "evidence_view"]

_VERIFIED, _FAILED, _UNVERIFIED = "verified", "failed", "unverified"


def _classify(outcome: Any) -> str:
    """Classify one claim's proof outcome, FAIL-CLOSED. A claim is VERIFIED only when it carries a
    `cleared` proof from a NAMED sealed floor; a `failed` proof reads FAILED; anything else — absent,
    malformed, or a bare assertion (vouched, no proof) — reads UNVERIFIED, never passing."""
    if not isinstance(outcome, Mapping):
        return _UNVERIFIED                                  # malformed / absent -> unverified
    proof = outcome.get("proof")
    if proof == "cleared" and outcome.get("verified_by"):   # a real cleared proof from a named floor
        return _VERIFIED
    if proof == "failed":
        return _FAILED
    return _UNVERIFIED                                       # vouched (no proof) / unknown -> unverified


@dataclass(frozen=True)
class VerifyStatus:
    """One claim's verification verdict — `verified` only on a cleared proof from a named floor; `failed`
    on a failed proof; `unverified` otherwise (vouched, absent, or malformed). Frozen; read-only."""
    claim: str
    status: str                       # verified | failed | unverified
    verified_by: Optional[str]        # the sealed floor that cleared it (None unless verified)

    @property
    def verified(self) -> bool:
        return self.status == _VERIFIED

    @classmethod
    def of(cls, claim: str, outcome: Any) -> "VerifyStatus":
        st = _classify(outcome)
        vb = outcome.get("verified_by") if (st == _VERIFIED and isinstance(outcome, Mapping)) else None
        return cls(claim=claim, status=st, verified_by=vb)


def verify_surface(proofs: Mapping[str, Any], *, mandate: Optional[str] = None,
                   scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render a read-only surface of verification verdicts. `proofs` = ``{claim_id: outcome}``; each is
    classified verified/failed/unverified FAIL-CLOSED and rendered through the Sovereign Lens. The
    surface shows what **verified**, never what is **vouched**; a failed or absent proof reads as such,
    never hidden. It renders the sealed floors' verdicts — it verifies nothing itself (no second
    authority) — and rolls no cryptography."""
    statuses = {}
    for cid, outcome in proofs.items():
        s = VerifyStatus.of(cid, outcome)
        statuses[cid] = {"status": s.status, "verified_by": s.verified_by}
    return render_view(statuses, mandate=mandate, scope=scope)


def is_verified(proofs: Mapping[str, Any], claim: str) -> bool:
    """FAIL-CLOSED gate: True ONLY if `claim` carries a cleared proof from a named floor. An absent,
    failed, malformed, or merely-vouched claim is False — the surface trusts nothing it cannot prove."""
    return claim in proofs and _classify(proofs[claim]) == _VERIFIED


def evidence_view(evidence_state: Mapping[str, Any], *, mandate: Optional[str] = None,
                  scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render the in-tree `evidence` module's state **READ-ONLY** (its actions projection / export
    packet) through the Lens — a display of evidence, **NOT** a composed sealed floor. It renders a
    supplied snapshot; it imports and runs no evidence engine, and asserts no verified-floor status for
    the evidence it shows (the yield_organism standing disposition, applied)."""
    return render_view(dict(evidence_state), mandate=mandate, scope=scope)
