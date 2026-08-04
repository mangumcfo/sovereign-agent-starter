"""Org model — a governed role lattice and organizational hierarchy, where a role is a named mandate.

Co-extrusion for s5_13 (Human Capital & Sovereign Payroll). Pure / structural, no crypto substrate (runs in a pure
public clone, no skip -- F-1 posture). An organization is a set of roles arranged in a reporting hierarchy; each role
is a named mandate -- the unit the sealed segregation-of-duties and access surface (S5-V2) scopes, so this volume adds
the organizational SHAPE, not a second access system. The structure is validated fail-closed: every reporting manager
is a defined role, and there is no cycle in the reporting graph. An employee holds a role and moves through a governed
lifecycle -- applicant → active → on_leave → terminated -- only by allowed, receipted transitions."""
from __future__ import annotations

from typing import Dict, List, Mapping, Set, Tuple

EMP_LIFECYCLE = ("applicant", "active", "on_leave", "terminated")
_EMP_ALLOWED: Dict[str, Set[str]] = {
    "applicant": {"active"},
    "active": {"on_leave", "terminated"},
    "on_leave": {"active", "terminated"},
    "terminated": set(),
}


class OrgError(ValueError):
    """Raised for an undefined reporting manager, a cycle in the reporting graph, or a missing mandate."""


class EmployeeError(ValueError):
    """Raised for an illegal employee-lifecycle transition."""


def validate_org(roles: Mapping[str, Mapping]) -> None:
    """Fail-closed validation of a role lattice. Each role maps a role id to a mapping with `reports_to` (another role
    id, or None for a top role) and `mandate` (a non-empty name -- the governed authority the role carries). Refuses an
    undefined reporting manager, a missing mandate, or a cycle in the reporting graph (a manager who reports, up the
    chain, to themselves -- an organization with no top)."""
    if not roles:
        raise OrgError("empty role lattice")
    for rid, r in roles.items():
        mgr = r.get("reports_to")
        if mgr is not None and mgr not in roles:
            raise OrgError(f"role {rid!r} reports to {mgr!r}, which is not a defined role")
        if not r.get("mandate"):
            raise OrgError(f"role {rid!r} has no mandate")
    for rid in roles:
        seen: Set[str] = set()
        cur = rid
        while cur is not None:
            if cur in seen:
                raise OrgError(f"reporting cycle through role {rid!r}")
            seen.add(cur)
            cur = roles[cur].get("reports_to")


def management_chain(roles: Mapping[str, Mapping], role: str) -> List[str]:
    """The chain of roles from `role` up to the top of the organization (exclusive of role itself)."""
    if role not in roles:
        raise OrgError(f"role {role!r} not in the lattice")
    chain: List[str] = []
    cur = roles[role].get("reports_to")
    while cur is not None:
        chain.append(cur)
        cur = roles[cur].get("reports_to")
    return chain


def employee_transition(employee: Mapping, to_status: str, period: str) -> Tuple[Dict, Dict]:
    """Move an employee to `to_status`, fail-closed: the lifecycle must permit applicant→active→on_leave→terminated
    with no illegal jump (you cannot terminate an applicant who was never active, or reactivate a terminated record).
    Returns (new_employee, event); the input is not mutated and the event is a receipted record of the move."""
    frm = employee.get("status", "applicant")
    if to_status not in _EMP_ALLOWED.get(frm, set()):
        raise EmployeeError(f"employee {employee.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                            f"(allowed from {frm!r}: {sorted(_EMP_ALLOWED.get(frm, set())) or 'none'})")
    ne = dict(employee)
    ne["status"] = to_status
    event = {"employee": employee.get("id"), "from": frm, "to": to_status, "period": period}
    return ne, event
