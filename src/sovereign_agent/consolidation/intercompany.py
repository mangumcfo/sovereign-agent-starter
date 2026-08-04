"""Intercompany — governed intercompany transactions recorded as a matched pair across two entity ledgers, so the
group can eliminate them on consolidation.

Co-extrusion for s5_18 (Multi-Entity & Consolidation). Pure / structural, no crypto substrate (F-1 pure-clone-clean).
An intercompany transaction (a sale, a charge, a loan between two entities of the same group) is booked in BOTH
entities under a shared intercompany id: the seller books an intercompany receivable against its own revenue account,
and the buyer books its expense account against an intercompany payable. The two sides are equal and opposite, so the
intercompany accounts NET TO ZERO at the group -- which is exactly what consolidation eliminates, leaving only third-
party activity. Composes the sealed double-entry posting floor (S5-V7); a one-sided entry or a self-dealing entity is
refused."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Set, Union

from ..financials.posting import Line, post

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class IntercompanyError(ValueError):
    """Raised for a non-positive amount, or an intercompany transaction whose two sides are the same entity."""


def record_intercompany(ic_id: str, seller: str, buyer: str, amount: Number,
                        seller_account: str, buyer_account: str, memo: str = "") -> Dict:
    """Book an intercompany transaction as a matched, balanced pair across the two entities.

    Returns a record carrying the shared `ic_id`, the amount, the two intercompany accounts introduced
    (`IC_receivable:<buyer>` in the seller, `IC_payable:<seller>` in the buyer), and `entries` — one balanced posting
    per entity (built on the sealed posting floor). The seller debits the intercompany receivable and credits
    `seller_account`; the buyer debits `buyer_account` and credits the intercompany payable. Equal and opposite by
    construction, so at the group the two intercompany accounts net to zero. Refuses a non-positive amount or
    seller == buyer."""
    amt = _dec(amount)
    if amt <= 0:
        raise IntercompanyError(f"intercompany amount must be > 0 (got {amt})")
    if seller == buyer:
        raise IntercompanyError(f"intercompany requires two distinct entities (got {seller!r} twice)")
    ic_receivable = f"IC_receivable:{buyer}"
    ic_payable = f"IC_payable:{seller}"
    seller_posting = post([Line.dr(ic_receivable, amt), Line.cr(seller_account, amt)],
                          memo=f"IC {ic_id} {seller}->{buyer}: {memo}".strip())
    buyer_posting = post([Line.dr(buyer_account, amt), Line.cr(ic_payable, amt)],
                         memo=f"IC {ic_id} {seller}->{buyer}: {memo}".strip())
    return {
        "ic_id": ic_id,
        "amount": str(amt),
        "seller": seller,
        "buyer": buyer,
        "ic_accounts": [ic_receivable, ic_payable],
        "entries": {seller: seller_posting, buyer: buyer_posting},
    }


def intercompany_accounts(records: Iterable[Dict]) -> Set[str]:
    """The set of intercompany accounts introduced by these records — exactly the accounts consolidation eliminates so
    the group shows no intercompany receivable or payable, only third-party balances."""
    accts: Set[str] = set()
    for r in records:
        accts.update(r["ic_accounts"])
    return accts
