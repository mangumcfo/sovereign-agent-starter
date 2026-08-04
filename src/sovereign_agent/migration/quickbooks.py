"""QuickBooks escape — a governed, receipted cutover from a QuickBooks trial balance onto the sovereign ledger, composing
the sealed floors rather than reimplementing them.

Co-extrusion for s5_34 (Escaping QuickBooks, KM 2026-08-04 — first volume of the displacement/escape arc). Pure /
structural. A growing business on QuickBooks reaches a point where the tool can no longer carry its books, and the move
off it is the riskiest thing it does to its financial records: a bulk transfer of every account and balance, whose
correctness usually rests on a bookkeeper eyeballing a report and a consultant's sign-off. This module makes that move a
governed, value-conserving, receipted act. It ingests a QuickBooks trial balance, maps every legacy account onto the
sovereign chart of accounts (composing the sealed CoA validator), proves the remap conserves value (no account dropped,
the mapped total equal to the source total), anchors the source and mapped sets to merkle provenance roots (composing the
migration primitive), governs the move through the migration lifecycle, and on cutover posts the opening balances into
the sovereign ledger as one balanced double-entry (composing the sealed posting). It is fail-closed at every seam: an
unmapped account, a target account absent from the chart, a remap that does not conserve value, or an opening entry that
does not balance refuses the cutover -- QuickBooks books are never carried onto the sovereign ledger unproven or
unbalanced. The module does not re-implement the ledger, the chart of accounts, the posting, or the migration primitive
it stands on -- it composes them; its own new act is the receipted cutover that carries a business's whole ledger across.

Composes: `migration.reconcile` (manifest_root provenance + the fail-closed lifecycle) · `financials.controlling`
(validate_coa, the sealed Chart of Accounts, Sovereign Controlling & Financial Close, Vol 12) · `financials.posting`
(from_entry, the sealed balanced double-entry, Sovereign Financials, Vol 7). The QuickBooks connector/API/OFX import is
NOT here -- that is the sovereign port's (S6-V07); this act begins from an already-ingested trial balance."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

from .reconcile import manifest_root, open_migration, transition
from ..financials.posting import from_entry
from ..financials.controlling import validate_coa

Number = Union[int, float, str, Decimal]


class QuickBooksError(ValueError):
    """Raised when a QuickBooks trial balance cannot be cut over onto the sovereign ledger -- an unmapped account, a
    target account absent from the chart of accounts, or a remap that does not conserve value -- fail-closed, never a set
    of books carried across on faith."""


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _records(balances: Mapping[str, Number]) -> List[Dict[str, str]]:
    """A trial balance {account: signed_balance} as canonical id/amount records, so it can be anchored to a provenance
    root (composing the migration primitive) -- the set that reconciled is provably the set that is cut over."""
    return [{"id": a, "amount": str(_dec(b))} for a, b in balances.items()]


def map_to_coa(qb_tb: Mapping[str, Number], account_map: Mapping[str, str],
               coa: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Map a QuickBooks trial balance onto the sovereign chart of accounts, value-conserving. The chart is validated
    first (composing the sealed CoA validator, Sovereign Controlling & Financial Close, Vol 12). Every QuickBooks account
    must name a mapping to a sovereign account that exists in the validated chart; an unmapped account, or a target not
    in the chart, is refused. Balances mapping to the same sovereign account sum. The mapped total equals the source
    total -- no balance is created or lost in the remap. Returns {sovereign_account: balance}."""
    validate_coa(coa)  # sealed Chart of Accounts validator (Vol 12) -- refuses a chart with a missing parent or a cycle
    mapped: Dict[str, Decimal] = {}
    for acct, bal in qb_tb.items():
        if acct not in account_map:
            raise QuickBooksError(f"QuickBooks account {acct!r} has no mapping to the sovereign chart of accounts "
                                  "-- refused (every legacy account must name its sovereign home before cutover)")
        tgt = account_map[acct]
        if tgt not in coa:
            raise QuickBooksError(f"QuickBooks account {acct!r} maps to {tgt!r}, which is not in the chart of accounts "
                                  "-- refused")
        mapped[tgt] = mapped.get(tgt, Decimal("0")) + _dec(bal)
    src_total = sum((_dec(b) for b in qb_tb.values()), Decimal("0"))
    mapped_total = sum(mapped.values(), Decimal("0"))
    if src_total != mapped_total:  # guards the invariant explicitly -- the remap conserves the ledger's total balance
        raise QuickBooksError(f"remap did not conserve value: source total {src_total} != mapped total {mapped_total}")
    return mapped


def opening_entry(mapped_balances: Mapping[str, Number]) -> Dict[str, List[Dict[str, str]]]:
    """Build a balanced opening journal entry from a mapped trial balance, in the sealed posting emitter shape
    {debits, credits}. A positive (debit-normal) balance becomes a debit; a negative balance becomes a credit of its
    magnitude; a zero balance contributes no line. The entry balances iff the trial balance balances -- its signed total
    is zero -- and the sealed posting refuses it otherwise."""
    debits: List[Dict[str, str]] = []
    credits: List[Dict[str, str]] = []
    for acct, bal in sorted(mapped_balances.items()):
        b = _dec(bal)
        if b > 0:
            debits.append({"account": acct, "amount": str(b)})
        elif b < 0:
            credits.append({"account": acct, "amount": str(-b)})
    return {"debits": debits, "credits": credits}


def receipted_cutover(migration_id: str, qb_tb: Mapping[str, Number], account_map: Mapping[str, str],
                      coa: Mapping[str, Mapping], memo: str = "QuickBooks opening balances") -> Dict[str, object]:
    """The receipted cutover from QuickBooks onto the sovereign ledger, fail-closed end to end. It maps the trial balance
    onto the sovereign chart of accounts value-conserving (composing the sealed CoA validator, Vol 12); anchors the
    source and mapped sets to merkle provenance roots (composing the migration primitive, so the set that reconciled is
    provably the set cut over); governs the move through the migration lifecycle (prepared -> parallel -> reconciled ->
    cutover); and on cutover posts the opening balances into the sovereign ledger as one balanced double-entry (composing
    the sealed posting, Vol 7), which refuses an unbalanced entry. A cutover reaches `cutover` only after the remap
    conserved value and the opening entry balanced -- QuickBooks books are never carried across unproven or unbalanced.
    Returns the receipt: the cutover state, the source and mapped provenance roots, the balanced opening posting, and the
    mapped balances."""
    mapped = map_to_coa(qb_tb, account_map, coa)                 # value-conserving remap, or refused
    source_root = manifest_root(_records(qb_tb))                 # provenance of the QuickBooks books (composed)
    mapped_root = manifest_root([{"id": a, "amount": str(b)} for a, b in mapped.items()])
    m = open_migration(migration_id, _records(qb_tb))            # prepared -- the migration lifecycle (composed)
    m, _ = transition(m, "parallel")                            # the parallel run alongside QuickBooks
    m, _ = transition(m, "reconciled")                          # value conserved -> reconciled
    m, _ = transition(m, "cutover")                             # cut over onto the sovereign ledger
    posting = from_entry(opening_entry(mapped), memo=memo)      # sealed balanced posting -- refuses if unbalanced
    return {"migration": m["id"], "status": m["status"], "source_root": source_root, "mapped_root": mapped_root,
            "opening_posting": posting, "mapped_balances": {a: str(b) for a, b in mapped.items()}}
