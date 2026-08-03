"""Audit checks — the compliance-automation floor: policy-as-checks over governed state, continuous audit-readiness,
and gaps that are refused or receipted (never silently omitted).

Co-extrusion for s5_14 (Compliance & Audit Automation + Reporting, KM Option B 2026-08-03). Pure / structural, no crypto
substrate (runs in a pure public clone, no skip — F-1 posture). A standard is not a document a team is trusted to
follow; it is a named, versioned set of governed checks -- predicates over the governed ledger state. Running the checks
either *receipts* each result (continuous monitoring, gaps recorded as receipted findings) or *enforces* them (refuses
on the first gap). Audit-readiness is the aggregate: are all checks passing, and if not, exactly which gaps remain. The
jurisdiction- and standard-specific check *libraries* are this volume's own in-volume growth (S5-V16); the enforcement
floor is here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping


class ComplianceGap(RuntimeError):
    """Raised by enforce_checks on the first failing check — a governed refusal of an out-of-compliance state."""


@dataclass(frozen=True)
class Check:
    """A single policy-as-check: an id, a human description, and a predicate over the governed state.

    The predicate returns True when the state satisfies the rule. It must be a pure function of the state it is given,
    so the check is reproducible: a successor, or an auditor, re-runs it against the governed state and gets the same
    verdict."""
    id: str
    description: str
    predicate: Callable[[Mapping], bool]


def standard_from_checks(name: str, version: str, checks: List[Check]) -> Dict[str, object]:
    """A standard is a named, versioned set of governed checks. Ingesting or mapping a standard means expressing it as
    this set; the standard is then reproducible and auditable rather than a PDF a team is trusted to remember."""
    if not name or not version:
        raise ValueError("a standard needs a name and a version")
    if not checks:
        raise ValueError("a standard needs at least one check")
    ids = [c.id for c in checks]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate check ids in standard")
    return {"name": name, "version": version, "checks": list(checks)}


def run_checks(checks: List[Check], state: Mapping) -> List[Dict[str, object]]:
    """Run the checks against the governed state and RECEIPT every result -- continuous-monitoring mode.

    Each result records the check id, description, whether it passed, and a `gap` note when it failed. A failing check
    is a receipted finding, not a silent omission: the gap is on the record, ready for remediation, and re-running the
    checks after the fix shows it closed. A predicate that raises is itself a failed (receipted) check, never a crash
    that hides the gap."""
    results: List[Dict[str, object]] = []
    for c in checks:
        try:
            passed = bool(c.predicate(state))
            gap = "" if passed else f"{c.description} — not satisfied"
        except Exception as e:  # a broken predicate is a receipted gap, not a hidden pass
            passed = False
            gap = f"{c.description} — check errored: {e}"
        results.append({"check": c.id, "description": c.description, "passed": passed, "gap": gap})
    return results


def enforce_checks(checks: List[Check], state: Mapping) -> None:
    """Enforce the checks -- REFUSE mode: raise ComplianceGap on the first failing check, naming it. Use where a state
    must not be allowed to proceed out of compliance (the preventive complement to receipted monitoring)."""
    for r in run_checks(checks, state):
        if not r["passed"]:
            raise ComplianceGap(f"compliance gap [{r['check']}]: {r['gap']}")


def audit_readiness(results: List[Mapping]) -> Dict[str, object]:
    """Aggregate a run into an audit-readiness view: are all checks passing, how many, and exactly which gaps remain.

    Readiness is a fact computed from the receipted results, not an assertion: 'audit-ready' means every governed check
    passed against the current state, and any gap is named rather than hidden behind a green light."""
    total = len(results)
    gaps = [{"check": r["check"], "gap": r["gap"]} for r in results if not r["passed"]]
    passed = total - len(gaps)
    return {"ready": len(gaps) == 0, "total": total, "passed": passed, "gaps": gaps}
