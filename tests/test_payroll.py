"""Payroll invariants — co-extrusion for s5_13 (Human Capital & Payroll).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves gross-to-net is
VALUE-CONSERVING -- gross == net + sum(named deductions) -- per payslip and across a batch, and that an over-withheld
payslip is refused."""
from decimal import Decimal
import pytest
from sovereign_agent.hr import compute_pay, run_payroll, PayrollError


def test_payslip_conserves_value():
    s = compute_pay("5000", {"tax_withholding": "1200", "benefits": "300", "garnishment": "150"})
    assert s["net"] == Decimal("3350.00")
    assert s["gross"] == s["net"] + s["total_deductions"]              # value-conserving
    assert set(s["deductions"]) == {"tax_withholding", "benefits", "garnishment"}   # every deduction named


def test_over_withholding_and_negatives_refused():
    with pytest.raises(PayrollError):
        compute_pay("1000", {"tax": "1200"})                          # deductions exceed gross
    with pytest.raises(PayrollError):
        compute_pay("-100", {})                                       # negative gross
    with pytest.raises(PayrollError):
        compute_pay("1000", {"tax": "-50"})                           # negative deduction


def test_batch_payroll_conserves_value():
    run = run_payroll([
        {"employee": "E1", "gross": "5000", "deductions": {"tax": "1000"}},
        {"employee": "E2", "gross": "4000", "deductions": {"tax": "800", "benefits": "200"}},
    ])
    assert run["balances"] is True
    assert run["total_gross"] == run["total_net"] + run["total_deductions"]
    assert run["total_gross"] == Decimal("9000.00")
