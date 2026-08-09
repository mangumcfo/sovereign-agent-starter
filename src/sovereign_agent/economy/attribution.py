# -*- coding: utf-8 -*-
"""economy.attribution — Sovereign Value Attribution (Series 10 Sovereign Economy, Vol 3).

`attribute_value` splits the value of a shared unit of work across its contributors **as records** — each
contributor's share is an income attribution *they own* — not as a settlement anyone performs. It composes
the sealed Income Primitive (S10 Vol 1, `attribute_income`) and nothing else: each contributor's share is
recorded through `attribute_income` as a credit-split record scoped to that contributor's mandate, so every
contributor owns their share, the shares are records rather than value movement, and value itself rides the
sealed Port. There is no central attributor and no held value — the attribution is a set of owned records,
each verifiable by the contributor who holds it.

Kill-targets: **composes V01 only** (imports the Income Primitive; rolls no crypto, holds no value, writes
no registry of its own) · **splits are records, not value movement** (money-path OFF — a share is a credit
record; value rides the Port; any in-node money-path in a split is refused by V01) · **each contributor
owns their share** (scoped to the contributor's mandate; no central attributor owns the split) ·
**weakest-party verifiable** (each contributor confirms their share from a receipt they hold, no platform,
no second device, no expertise). A contribution's bearing on reputation and mutual credit homes OUT to
Sovereign Risk & Mutual Protection (S11); its inheritance to Generational Transfer (S12).
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from .income import attribute_income, verify_income, IncomeRefused, IncomeStatus  # S10 Vol 1 — composed by identity

__all__ = ["attribute_value", "verify_attribution", "IncomeRefused", "IncomeStatus"]


def attribute_value(value_ref: str, contributors: Sequence[Tuple[str, Any]], *, author: str,
                    source_ref: str, at: str, registry: Any, mandate_of: Any = None,
                    port_ref: Optional[str] = None, gate: Any = None,
                    action_class: str = "attribute_value",
                    role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Attribute the value of `value_ref` across `contributors` (a sequence of `(contributor, share)`), each
    as an income attribution the contributor OWNS. Composes `attribute_income` (S10 Vol 1) once per
    contributor, recording the share as a credit-split record scoped to that contributor's mandate. Splits
    are records, not value movement — value rides the sealed Port (via `port_ref`); no value is held.
    Returns `{contributor: receipt}`. `mandate_of` maps a contributor to their mandate (default: the
    contributor owns their own share)."""
    if not contributors:
        raise IncomeRefused("value attribution needs at least one contributor")
    receipts = {}
    for contributor, share in contributors:
        if callable(mandate_of):
            mandate = mandate_of(contributor)
        else:
            mandate = mandate_of or contributor            # default: the contributor owns their own share
        r = attribute_income(contributor, value_ref, mandate=mandate, author=author, source_ref=source_ref,
                             at=at, registry=registry, port_ref=port_ref,
                             extra={"value_ref": str(value_ref), "share": str(share)}, gate=gate,
                             action_class=action_class, role_spec=role_spec, mode=mode)
        receipts[str(contributor)] = r
    return receipts


def verify_attribution(receipt: Mapping[str, Any], contributor: str, value_ref: str, share: Any, *,
                       port_ref: Optional[str] = None) -> IncomeStatus:
    """Weakest-party check: a contributor confirms their SHARE of a value from the receipt they hold — no
    platform, no second device, no expertise. Composes `verify_income` (S10 Vol 1) over the contributor's
    credit-split record; a tampered share, contributor, or value flips the green light."""
    return verify_income(receipt, contributor, value_ref, port_ref=port_ref,
                         extra={"value_ref": str(value_ref), "share": str(share)})
