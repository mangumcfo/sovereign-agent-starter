"""Payroll — a value-conserving gross-to-net computation where every deduction is named.

Co-extrusion for s5_13 (Human Capital & Sovereign Payroll). Pure arithmetic over Decimal, no crypto substrate (F-1
pure-clone-clean). A payslip starts from gross pay and subtracts a set of NAMED deductions -- tax withholding (composed
from the sealed tax surface), benefits, garnishments -- to reach net pay, and it is value-conserving by construction:
`gross == net + sum(deductions)` to the cent. Every deduction is named and carried on the payslip, so a payslip is
never a net figure taken on trust -- it is a computation whose every subtraction is on the record. A deduction set that
would drive net pay below zero is refused, not silently capped. A payroll run over many employees conserves value at
the batch level too: the sum of gross equals the sum of net plus the sum of deductions."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Union

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class PayrollError(ValueError):
    """Raised for a negative gross/deduction, or a deduction set that exceeds gross (net would be negative)."""


def compute_pay(gross: Number, deductions: Mapping[str, Number]) -> Dict[str, object]:
    """Compute a value-conserving payslip: net = gross minus the sum of the named deductions. Refuses a negative gross,
    a negative deduction, or a total deduction that exceeds gross (net cannot be negative -- an over-withheld payslip is
    a data error, not a payslip). Returns the gross, the named deductions, the total deducted, and the net; the payslip
    satisfies `gross == net + total_deductions` by construction."""
    g = _dec(gross)
    if g < 0:
        raise PayrollError(f"gross pay must be >= 0 (got {g})")
    named: Dict[str, Decimal] = {}
    total = Decimal("0")
    for name, amt in deductions.items():
        d = _dec(amt)
        if d < 0:
            raise PayrollError(f"deduction {name!r} must be >= 0 (got {d})")
        named[name] = d.quantize(_CENTS)
        total += named[name]
    if total > g:
        raise PayrollError(f"deductions {total} exceed gross {g} -- net pay cannot be negative")
    net = (g - total).quantize(_CENTS)
    return {"gross": g.quantize(_CENTS), "deductions": named, "total_deductions": total.quantize(_CENTS), "net": net}


def run_payroll(payslips: Iterable[Mapping]) -> Dict[str, object]:
    """Run payroll over many employees, each a mapping with `employee`, `gross`, and `deductions`. Returns the per-
    employee payslips and the batch totals, which conserve value: the sum of gross equals the sum of net plus the sum
    of all deductions. A batch is not a black-box total -- it is the sum of value-conserving payslips, each auditable."""
    slips: List[Dict] = []
    tg = tn = td = Decimal("0")
    for p in payslips:
        slip = compute_pay(p["gross"], p.get("deductions", {}))
        slip["employee"] = p.get("employee")
        slips.append(slip)
        tg += slip["gross"]; tn += slip["net"]; td += slip["total_deductions"]
    return {"payslips": slips, "total_gross": tg, "total_net": tn, "total_deductions": td,
            "balances": tg == tn + td}
