"""Consolidation — the group view as a PROJECTION over governed entity ledgers.

Co-extrusion for s5_18 (Multi-Entity & Consolidation) and the SPINE of the volume. Pure / structural, no crypto
substrate (F-1 pure-clone-clean). The consolidated group numbers are never a second, mutable copy of the truth: they
are DERIVED, on every call, from the entity ledgers -- each entity's trial balance is translated into the group's
reporting currency at a governed FX rate, the translations are summed, and the intercompany balances are eliminated.
The projection is value-conserving by construction: every entity posting balanced (its trial balance nets to zero),
FX-translation rounding is booked to a cumulative-translation-adjustment so each translated entity still nets to zero,
and each intercompany pair is equal and opposite -- so the group trial balance nets to zero too.

Composes sealed floors: `financials.posting.trial_balance` (S5-V7, the entity ledgers), `financials.fx.convert`
(translation at a supplied, receipted rate -- the live rate feed is homed in S6-V07, not here), and
`consolidation.entities` (the group membership control implies). The FX rate is an input the caller is accountable
for; this module sources nothing over a wire."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

from ..financials.posting import trial_balance
from ..financials.fx import convert
from .entities import validate_structure, group_members
from .intercompany import intercompany_accounts

Number = Union[int, float, str, Decimal]

CTA_ACCOUNT = "cumulative_translation_adjustment"


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ConsolidationError(ValueError):
    """Raised when an entity in the group is in a non-group currency but no FX rate to the group currency was given."""


def consolidate(entities: Mapping[str, Mapping], root: str, entity_postings: Mapping[str, List[Dict]],
                group_currency: str, fx_rates: Mapping[str, Number] = None,
                intercompany_records=None) -> Dict[str, object]:
    """Project the consolidated group view for the group under `root`. This is a read-only projection: it computes the
    group from the inputs and returns it; it never stores or mutates a consolidated ledger.

    - `entities`: the validated registry (id -> {parent, ownership_pct, currency}).
    - `entity_postings`: id -> that entity's list of balanced postings (its ledger; intercompany postings included).
    - `group_currency`: the group's reporting currency.
    - `fx_rates`: from-currency -> rate into `group_currency`; required for any group entity not already in it.
    - `intercompany_records`: the intercompany pairs (from `intercompany.record_intercompany`) to eliminate.

    Returns `{group_currency, members, entity_balances (per entity, translated), eliminations, group, balances}`.
    `group` is the consolidated trial balance; `balances` is True when it nets to zero (value-conserving)."""
    validate_structure(entities)
    members = group_members(entities, root)
    fx_rates = dict(fx_rates or {})

    per_entity: Dict[str, Dict[str, Decimal]] = {}
    group: Dict[str, Decimal] = {}
    for eid in sorted(members):
        tb = trial_balance(entity_postings.get(eid, []))
        ccy = entities[eid]["currency"]
        if ccy != group_currency:
            rate = fx_rates.get(ccy)
            if rate is None:
                raise ConsolidationError(
                    f"entity {eid!r} reports in {ccy} but no FX rate to {group_currency} was supplied")
            translated: Dict[str, Decimal] = {}
            for acct, amt in tb.items():
                translated[acct] = convert(amt, ccy, group_currency, rate)["to"]["amount"]
            # translation rounds each account to cents, which can break the zero-sum; book the residual to the
            # cumulative-translation-adjustment so the translated entity still balances (real consolidation practice).
            residual = sum(translated.values(), Decimal("0"))
            if residual != 0:
                translated[CTA_ACCOUNT] = translated.get(CTA_ACCOUNT, Decimal("0")) - residual
            tb = translated
        per_entity[eid] = tb
        for acct, amt in tb.items():
            group[acct] = group.get(acct, Decimal("0")) + amt

    # Eliminate intercompany: zero the intercompany accounts at the group. Because each pair is equal and opposite
    # (same currency), removing both sides preserves the group's zero-sum -- value-conserving.
    ic_accts = intercompany_accounts(list(intercompany_records or []))
    eliminations: Dict[str, Decimal] = {}
    for acct in sorted(ic_accts):
        bal = group.get(acct, Decimal("0"))
        if bal != 0:
            eliminations[acct] = bal
            group[acct] = Decimal("0")

    group = {a: v for a, v in group.items() if v != 0}  # projection carries only live balances
    balances = sum(group.values(), Decimal("0")) == Decimal("0")
    return {
        "group_currency": group_currency,
        "members": sorted(members),
        "entity_balances": {e: {a: str(v) for a, v in tb.items()} for e, tb in per_entity.items()},
        "eliminations": {a: str(v) for a, v in eliminations.items()},
        "group": group,
        "balances": balances,
    }
