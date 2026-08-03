"""Reporting — management and statutory statements (P&L, balance sheet, cash flow) as report-as-projection from the
immutable ledger. Never a stored snapshot; always recomputed from the governed postings.

Co-extrusion for s5_14 (Compliance & Audit Automation + Reporting, KM Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). This discharges the reporting debt
homed to S5-V14 by the sealed volumes (Financials Vol-7 Ch4 and the Ch6 does-not-do chapters of Treasury/Supply/Mfg/
Project/Controlling/Investment): a statement is a projection computed on demand from the trial balance and the
Chart-of-Accounts classification, and every reported figure is traceable to its postings. Jurisdiction-specific
statutory pack *formats* are this volume's own in-volume growth (S5-V16); a stored, un-recomputable statement is exactly
what this refuses to be."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

from .posting import trial_balance

Number = Union[int, float, str, Decimal]

# CoA account types (carried on the chart's per-account metadata, `controlling.validate_coa`)
DEBIT_NATURAL = {"asset", "expense"}
CREDIT_NATURAL = {"liability", "equity", "revenue"}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ReportingError(ValueError):
    """Raised when a statement cannot be projected — an account with no type in the chart, or a balance sheet that
    does not balance (which means the underlying postings were not balanced)."""


def _net_by_type(postings: List[Dict], coa: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Sum the trial-balance nets (debit − credit) per account type. Every posted account must be typed in the chart."""
    nets = trial_balance(postings)
    totals: Dict[str, Decimal] = {}
    for account, net in nets.items():
        meta = coa.get(account)
        if meta is None or "type" not in meta:
            raise ReportingError(f"account {account!r} has no type in the chart of accounts")
        t = meta["type"]
        totals[t] = totals.get(t, Decimal("0")) + net
    return totals


def income_statement(postings: List[Dict], coa: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Project a P&L from the governed postings: revenue − expense = net income.

    Revenue is credit-natural (its trial-balance net is negative), so it is reported as the negated net; expense is
    debit-natural and reported as its net. The figures are a projection of the ledger, not a stored total."""
    by = _net_by_type(postings, coa)
    revenue = -by.get("revenue", Decimal("0"))   # credit-natural -> positive revenue
    expense = by.get("expense", Decimal("0"))     # debit-natural -> positive expense
    return {"revenue": revenue, "expense": expense, "net_income": revenue - expense}


def balance_sheet(postings: List[Dict], coa: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Project a balance sheet: assets = liabilities + equity + net income, cross-footed fail-closed.

    Because every governed posting balances, the trial balance nets to zero and the sheet balances by construction; if
    it does not, the postings were not balanced and the projection is refused rather than presented wrong."""
    by = _net_by_type(postings, coa)
    assets = by.get("asset", Decimal("0"))            # debit-natural
    liabilities = -by.get("liability", Decimal("0"))  # credit-natural
    equity = -by.get("equity", Decimal("0"))
    revenue = -by.get("revenue", Decimal("0"))
    expense = by.get("expense", Decimal("0"))
    net_income = revenue - expense
    rhs = liabilities + equity + net_income
    if assets != rhs:
        raise ReportingError(f"balance sheet does not balance: assets {assets} != L+E+NI {rhs} "
                             "(underlying postings are not balanced)")
    return {"assets": assets, "liabilities": liabilities, "equity": equity,
            "net_income": net_income, "total_liabilities_and_equity": rhs}


def cash_flow_statement(movements: List[Mapping]) -> Dict[str, Decimal]:
    """Project a cash-flow statement: net cash change classified into operating / investing / financing.

    Each movement is a mapping with `activity` (one of operating/investing/financing) and a signed `amount` (inflow
    positive, outflow negative). The net change ties to the sum of the three activities by construction."""
    buckets = {"operating": Decimal("0"), "investing": Decimal("0"), "financing": Decimal("0")}
    for m in movements:
        act = m.get("activity")
        if act not in buckets:
            raise ReportingError(f"cash movement has unknown activity {act!r}")
        buckets[act] += _dec(m["amount"])
    buckets["net_change"] = buckets["operating"] + buckets["investing"] + buckets["financing"]
    return buckets
