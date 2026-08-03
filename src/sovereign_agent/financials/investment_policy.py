"""Investment-policy enforcement — policy as code that refuses a capital move it forbids.

Co-extrusion for s5_41 (Sovereign Treasury Investment & Financing, KM Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). An investment policy is not a PDF a
committee is trusted to remember; it is enforced code. This module checks a proposed investment against a policy --
per-issuer exposure cap, an allowed-instrument set, and a maximum single-issuer concentration -- against the existing
governed positions, and refuses fail-closed a move that would violate it. Policy *optimization* (choosing the best
allocation) is analytics, homed in S5-V17; this is enforcement, not optimization."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

from .investment import total_by_issuer

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class PolicyViolation(ValueError):
    """Raised (or reported) when a proposed investment would violate the enforced policy."""


def check_investment(policy: Mapping, proposed: Mapping, existing: Iterable[Mapping]) -> Dict[str, object]:
    """Enforce an investment policy against a proposed move, given the existing governed positions.

    `proposed` is a position move (issuer, instrument, currency, amount>0 to acquire). `policy` may carry:
      - `allowed_instruments`: a set/list; a proposed instrument outside it is refused.
      - `issuer_caps`: {issuer: max_exposure} in the proposed currency; the post-move issuer exposure may not exceed it.
      - `max_concentration`: a Decimal fraction (0..1); no single issuer's exposure may exceed this share of the total.
    Returns {"ok": True} if the move is allowed, else {"ok": False, "violations": [...]} naming each broken rule. The
    check is fail-closed by construction -- a caller that requires approval treats any violation as a refusal."""
    violations = []
    issuer = proposed["issuer"]
    instrument = proposed["instrument"]
    currency = proposed["currency"]
    amount = _dec(proposed["amount"])

    allowed = policy.get("allowed_instruments")
    if allowed is not None and instrument not in set(allowed):
        violations.append(f"instrument {instrument!r} not in policy allowed set")

    # post-move issuer exposure in the proposed currency
    by_issuer = total_by_issuer(list(existing) + [proposed])
    post = by_issuer.get((issuer, currency), Decimal("0"))

    caps = policy.get("issuer_caps", {})
    if issuer in caps and post > _dec(caps[issuer]):
        violations.append(f"issuer {issuer!r} exposure {post} exceeds cap {_dec(caps[issuer])}")

    max_conc = policy.get("max_concentration")
    if max_conc is not None:
        total = sum((v for (i, c), v in by_issuer.items() if c == currency), Decimal("0"))
        if total > 0:
            share = post / total
            if share > _dec(max_conc):
                violations.append(
                    f"issuer {issuer!r} concentration {share:.4f} exceeds max {_dec(max_conc)}")

    return {"ok": not violations, "violations": violations}
