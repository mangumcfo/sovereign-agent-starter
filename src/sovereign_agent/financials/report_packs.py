"""Report packs — named, ordered sets of report-as-projection statements with labels (a management pack, a
statutory-style pack), assembled fail-closed from the living ledger.

Co-extrusion for s5_14 (Compliance & Audit + Reporting, KM Option B+ 2026-08-03). Pure / structural over the report
projections, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). A pack is the shape a real
deliverable takes: an ordered selection of the P&L, balance sheet, and cash flow, each under the label a given audience
(management) or standard (a statutory filing) uses. The pack is built by projecting each statement from the governed
postings; it is fail-closed -- a pack that requires a statement which cannot project (a balance sheet that does not
cross-foot, an unknown statement key) is refused rather than shipped incomplete. The jurisdiction-specific *layout* of a
statutory pack deepens within this volume; the pack surface itself runs today."""
from __future__ import annotations

from typing import Dict, List, Mapping, Tuple

from .reporting import income_statement, balance_sheet, cash_flow_statement

# canonical statement keys
INCOME = "income_statement"
BALANCE = "balance_sheet"
CASHFLOW = "cash_flow"
_STATEMENTS = (INCOME, BALANCE, CASHFLOW)

# named pack definitions: an ordered list of (statement_key, label)
MANAGEMENT_PACK: List[Tuple[str, str]] = [
    (INCOME, "Management P&L"),
    (BALANCE, "Management Balance Sheet"),
    (CASHFLOW, "Cash Flow Summary"),
]
STATUTORY_PACK: List[Tuple[str, str]] = [
    (BALANCE, "Statement of Financial Position"),
    (INCOME, "Statement of Comprehensive Income"),
    (CASHFLOW, "Statement of Cash Flows"),
]
PACKS: Dict[str, List[Tuple[str, str]]] = {"management": MANAGEMENT_PACK, "statutory": STATUTORY_PACK}


class PackError(ValueError):
    """Raised when a pack cannot be assembled — an unknown statement key, or a required statement that cannot project
    (which includes a balance sheet that does not cross-foot: reporting refuses it, and the pack refuses in turn)."""


def build_pack(pack_def: List[Tuple[str, str]], postings: List[Dict], coa: Mapping,
               cash_movements: List[Mapping]) -> Dict[str, object]:
    """Assemble a named report pack: each statement in the ordered definition, projected from the governed ledger and
    carried under its label. Fail-closed -- an unknown statement key is refused, and a statement that cannot project
    (e.g. a balance sheet that does not cross-foot) propagates its refusal rather than being omitted or plugged."""
    if not pack_def:
        raise PackError("empty pack definition")
    statements = []
    for key, label in pack_def:
        if key not in _STATEMENTS:
            raise PackError(f"unknown statement key {key!r}")
        if key == INCOME:
            value = income_statement(postings, coa)
        elif key == BALANCE:
            value = balance_sheet(postings, coa)      # raises ReportingError if it does not cross-foot
        else:
            value = cash_flow_statement(cash_movements)
        statements.append({"key": key, "label": label, "statement": value})
    return {"statements": statements, "count": len(statements)}


def build_named_pack(name: str, postings: List[Dict], coa: Mapping,
                     cash_movements: List[Mapping]) -> Dict[str, object]:
    """Build one of the named packs (management / statutory) by name; refuse an unknown pack name."""
    if name not in PACKS:
        raise PackError(f"unknown pack {name!r} (known: {', '.join(PACKS)})")
    pack = build_pack(PACKS[name], postings, coa, cash_movements)
    pack["name"] = name
    return pack
