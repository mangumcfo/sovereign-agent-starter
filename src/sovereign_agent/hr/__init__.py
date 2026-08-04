"""HR — governed org/role model and lifecycle, and value-conserving gross-to-net payroll (s5_13)."""
from .org_model import (
    validate_org, management_chain, employee_transition, EMP_LIFECYCLE, OrgError, EmployeeError,
)
from .payroll import compute_pay, run_payroll, PayrollError

__all__ = [
    "validate_org", "management_chain", "employee_transition", "EMP_LIFECYCLE", "OrgError", "EmployeeError",
    "compute_pay", "run_payroll", "PayrollError",
]
