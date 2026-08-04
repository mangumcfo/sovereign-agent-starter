"""Org-model invariants — co-extrusion for s5_13 (Human Capital & Payroll).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the role lattice is
validated fail-closed (no cycle, no ghost manager) and the employee lifecycle is a fail-closed state machine."""
import pytest
from sovereign_agent.hr import validate_org, management_chain, employee_transition, OrgError, EmployeeError

ORG = {
    "CEO": {"reports_to": None, "mandate": "govern the enterprise"},
    "CFO": {"reports_to": "CEO", "mandate": "govern finance"},
    "Controller": {"reports_to": "CFO", "mandate": "govern the ledger"},
}


def test_management_chain_walks_to_the_top():
    assert management_chain(ORG, "Controller") == ["CFO", "CEO"]
    assert management_chain(ORG, "CEO") == []


def test_org_validation_refuses_bad_structure():
    with pytest.raises(OrgError):
        validate_org({"A": {"reports_to": "ghost", "mandate": "x"}})          # undefined manager
    with pytest.raises(OrgError):
        validate_org({"A": {"reports_to": None}})                            # no mandate
    with pytest.raises(OrgError):
        validate_org({"A": {"reports_to": "B", "mandate": "x"},
                      "B": {"reports_to": "A", "mandate": "y"}})              # cycle


def test_employee_lifecycle_is_fail_closed():
    e = {"id": "E1", "status": "applicant"}
    e2, ev = employee_transition(e, "active", "2026-01")
    assert e2["status"] == "active" and ev["to"] == "active" and e["status"] == "applicant"
    with pytest.raises(EmployeeError):
        employee_transition({"id": "E2", "status": "applicant"}, "terminated", "2026-01")   # never active
    with pytest.raises(EmployeeError):
        employee_transition({"id": "E3", "status": "terminated"}, "active", "2026-01")       # no reactivation
