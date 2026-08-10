# -*- coding: utf-8 -*-
"""estate.estate_covenant — Generational Transfer (Series 12, Vol 5, the CAPSTONE:
The Sovereign Estate as Living Covenant).

An estate that cannot be verified whole by the person who inherits it was never an estate — it was a promise.
This capstone brings the entire series together into one living covenant, and it does so by composing the
sealed Series-12 volumes and **inventing no new engine**. `inherit_estate` is the one covenant a resourceless
heir reads: it dispatches every element of a whole sovereign estate — the estate re-attribution (income,
protection, material — Vol 1), the keys (Vol 2), the ventures (Vol 3), and the family governance (Vol 4) — to
that element's own sealed verifier, and returns **one uniform indicator**, `this estate is mine now`, true only
when every element verifies as the heir's own and intact. A whole estate becomes inheritable in a single honest
green light: the heir needs no second device, no expertise, and no permission — just the receipts they hold.
Inheritance is **re-attribution of owned records** — the transfer receipt, the family key quorum, the venture
handoff, and the family constitution — **not a released fund or an escrowed asset an authority hands over.**

**The SUCCESSION-FENCE — the whole series' fence in one place:** no standing escrow · no second succession
authority · no recovery engine · family-own keys · composition-not-engine. `ESTATE_COVENANT_BREACH_FIELDS`
refuses any escrow, released fund, custodian, trust-company/executor authority, arbitration authority, recovery
engine, second authority, penalty, or (seal-key-closed) press/seal key — for any element of the stack.
KILL-TARGET: the trust company or executor that holds the estate in escrow and rations the handoff on its own
terms — refused; inheritance is records the heir verifies, not an estate an authority releases. Weakest-party
(the series' final test): **a resourceless heir verifies the whole estate — income, keys, ventures, and
governance — passed intact and theirs from the receipts they hold, on one honest indicator.** NO TOKEN · no
yield · holds no value · money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from .generational_transfer import verify_transfer, EstateRefused          # S12 V1 (estate re-attribution)
from .key_succession import recover_with_quorum                            # S12 V2 (keys)
from .venture_continuity import handoff_package                            # S12 V3 (ventures)
from .family_governance import weakest_party_protected                     # S12 V4 (family governance)

__all__ = ["inherit_estate", "verify_estate_element", "estate_stack_kinds",
           "EstateInheritance", "ESTATE_STACK_KINDS", "ESTATE_COVENANT_BREACH_FIELDS", "EstateRefused"]

# The elements of a whole sovereign estate, each verified by its own sealed Series-12 volume. The covenant
# COMPOSES these four load-bearing surfaces; it re-implements none of them.
ESTATE_STACK_KINDS = ("estate", "keys", "ventures", "governance")

# THE SUCCESSION-FENCE — the whole series' fence gathered in one place: inheritance is re-attribution of owned
# records, NOT a released fund or an escrowed asset. Any escrow, released fund, custodian, trust-company/
# executor authority, arbitration authority, recovery engine, second authority, penalty, or press/seal key is a
# breach — refused for any element of the stack.
ESTATE_COVENANT_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "escrowed_estate", "escrowed_asset", "held_estate", "released_fund",
    "release_authority", "second_authority", "succession_authority", "recovery_authority", "recovery_engine",
    "succession_engine", "custodian", "key_custodian", "trust_company", "executor_authority",
    "arbitration_authority", "dispute_custodian", "penalty", "forfeiture", "held_value",
    "seal_key", "press_key", "sealing_key",
})


def estate_stack_kinds() -> List[str]:
    """The element kinds a sovereign-estate covenant composes — one per sealed Series-12 volume (V1–V4)."""
    return list(ESTATE_STACK_KINDS)


@dataclass(frozen=True)
class EstateInheritance:
    """The one honest indicator a resourceless heir reads: *this estate is mine now* — inherited iff every
    element of the whole estate (income/estate, keys, ventures, governance) verifies as the heir's own and
    intact. Holds no value; a by-kind tally shows the shape of the inherited estate. The heir needs nothing but
    this single green light and the receipts they already hold."""
    inherited: bool
    reason: str
    heir: str
    verified_count: int
    by_kind: Dict[str, int] = field(default_factory=dict)


def _fence_element(element: Mapping[str, Any]) -> None:
    for k in element:
        if str(k).lower() in ESTATE_COVENANT_BREACH_FIELDS:
            raise EstateRefused(
                f"an estate-stack element must carry no escrow/second-authority/custodian field ('{k}') — "
                f"inheritance is re-attribution of owned RECORDS (the transfer receipt, the family key quorum, "
                f"the venture handoff, the family constitution), NOT a released fund or an escrowed asset an "
                f"authority hands over; the covenant composes the sealed Series-12 V1–V4 surfaces, it invents "
                f"no succession engine, and the family's keys stay the family's own")


def verify_estate_element(heir: str, element: Mapping[str, Any]) -> bool:
    """Verify ONE element of a whole estate by composing its own sealed Series-12 verifier. `element` is
    `{kind, ...}` where kind ∈ estate|keys|ventures|governance and the rest are the args that kind's sealed
    surface needs: `estate` → `verify_transfer` (Vol 1), `keys` → `recover_with_quorum` (Vol 2), `ventures` →
    `handoff_package(...).complete` (Vol 3), `governance` → `weakest_party_protected(...).protected` (Vol 4).
    The SUCCESSION-FENCE refuses any escrow / second-authority / custodian / recovery-engine / penalty / seal-key
    field — inheritance is a verified record, not a released fund."""
    kind = str(element.get("kind", "")).strip().lower()
    if kind not in ESTATE_STACK_KINDS:
        raise EstateRefused(
            f"unknown estate-stack element kind {element.get('kind')!r} — a covenant composes one of "
            f"{list(ESTATE_STACK_KINDS)} (sealed Series-12 V1–V4); it invents no new element")
    _fence_element(element)
    if kind == "estate":
        return verify_transfer(element["receipt"], heir, element["decedent"], element["work_ref"],
                               extra=element.get("extra"))
    if kind == "keys":
        return recover_with_quorum(element["epoch"], element["approvers"], element["policy"])
    if kind == "ventures":
        return handoff_package(element["state"]).complete
    # kind == "governance": the family governance protects the heir iff every decision that could override them
    # is gated (composes weakest_party_protected, Vol 4) — a constitution that leaves the heir exposed fails.
    return weakest_party_protected(element["constitution"], element["affecting_classes"]).protected


def inherit_estate(heir: str, stack: Sequence[Mapping[str, Any]]) -> EstateInheritance:
    """The Sovereign Estate Covenant: verify that a WHOLE sovereign estate is intact and inheritable by
    composing each element's own sealed Series-12 verifier (V1–V4) — one uniform check over any element kind
    (income/estate, keys, ventures, governance). Returns ONE honest indicator, `inherited`, true iff every
    element verifies as the `heir`'s own and intact (*this estate is mine now*), with a by-kind tally. It records
    nothing, holds no value, invents no engine, and rolls no cryptography. Deny-by-default: an empty estate is
    not inherited; a foreign or tampered element fails the whole; an escrow / second-authority / custodian /
    penalty / seal-key field is refused (the SUCCESSION-FENCE); an unknown kind is refused. This is the series'
    final test — a resourceless heir reads one green light over the whole estate from the receipts they hold."""
    by_kind = {k: 0 for k in ESTATE_STACK_KINDS}
    verified = 0
    reason: List[str] = []
    for i, element in enumerate(stack):
        if verify_estate_element(heir, element):     # composes the sealed floor; raises on fence/kind breach
            verified += 1
            by_kind[str(element.get("kind")).strip().lower()] += 1
        else:
            reason.append(f"element {i} ({element.get('kind')}) does not verify as {heir}'s own/intact")
    ok = bool(stack) and not reason
    return EstateInheritance(
        inherited=ok,
        reason="; ".join(reason) or "this estate is mine now — income, keys, ventures, and governance all verify",
        heir=heir, verified_count=verified, by_kind=by_kind)
