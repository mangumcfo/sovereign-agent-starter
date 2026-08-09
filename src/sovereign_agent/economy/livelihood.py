# -*- coding: utf-8 -*-
"""economy.livelihood — Sovereign Livelihood (Series 10 Sovereign Economy, Vol 2).

`attest_livelihood` establishes an earner's **livelihood** — their sustained economic standing — as a proof
built from the earner's **own income receipts**, not a score a platform computes about them. It composes the
sealed Income Primitive (S10 Vol 1, `verify_income`) and nothing else: a livelihood is established iff every
income the earner presents verifies as *theirs*. It records nothing new and holds no value — it is a
verification over receipts the earner already holds, so the earner proves their whole livelihood without a
platform, and a platform cannot manufacture or revoke a livelihood standing that lives in the earner's own
receipts.

Kill-targets: **composes V01 only** (imports the Income Primitive's `verify_income`; rolls no crypto, holds
no value, records no new object) · **a livelihood is the earner's own receipts, not a platform's profile**
(every income must verify as the earner's, or the livelihood is not established) · **money-path OFF**
(inherited — no value is held or moved; a livelihood is a proof, not a balance) · **weakest-party
verifiable** (the earner establishes their livelihood from the receipts they hold, no platform, no second
device, no expertise). A livelihood's standing among peers homes OUT to Peerhood (S14); a livelihood built
across generations to Generational Transfer (S12).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .income import verify_income, IncomeRefused        # S10 Vol 1 The Income Primitive — composed by identity

__all__ = ["attest_livelihood", "LivelihoodStatus", "IncomeRefused"]


@dataclass(frozen=True)
class LivelihoodStatus:
    """The earner's livelihood verdict: established iff every income presented verifies as theirs."""
    established: bool
    verified_count: int
    earner: str
    reason: str


def attest_livelihood(earner: str, incomes: Sequence[Mapping[str, Any]]) -> LivelihoodStatus:
    """Establish an earner's livelihood from their OWN income receipts. `incomes` is a sequence of records,
    each `{receipt, work_ref, amount?, unit?, port_ref?}`. Composes `verify_income` (S10 Vol 1) over each:
    the livelihood is established iff EVERY income verifies as the earner's — one income that is not theirs
    (or was tampered) fails the whole. Records nothing, holds no value; the earner proves their livelihood
    from receipts they hold, with no platform, no second device, no expertise."""
    if not str(earner).strip():
        raise IncomeRefused("a livelihood requires an earner")
    if not incomes:
        return LivelihoodStatus(False, 0, str(earner), "a livelihood needs at least one earning")
    verified = 0
    for item in incomes:
        work_ref = item.get("work_ref")
        st = verify_income(item["receipt"], earner, work_ref,
                           amount=item.get("amount"), unit=item.get("unit", "credits"),
                           port_ref=item.get("port_ref"), extra=item.get("extra"))
        if not st.provisioned:
            return LivelihoodStatus(False, verified, str(earner),
                                    f"income {work_ref!r} is not the earner's: {st.reason}")
        verified += 1
    return LivelihoodStatus(True, verified, str(earner),
                            f"livelihood established from {verified} owned earning(s)")
