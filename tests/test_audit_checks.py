"""Compliance-automation floor invariants — co-extrusion for s5_14 (Option B).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves policy-as-checks over
governed state -- a standard as a named/versioned check set, receipted monitoring (gaps recorded, not hidden), enforce
mode (refuse on gap), and audit-readiness aggregation."""
import pytest

from sovereign_agent.compliance.audit_checks import (
    Check, standard_from_checks, run_checks, enforce_checks, audit_readiness, ComplianceGap,
)

CHECKS = [
    Check("PERIODS-BALANCED", "every closed period balances", lambda s: s.get("periods_balanced", False)),
    Check("APPROVALS-PRESENT", "every material act carries a human approval", lambda s: s.get("all_approved", False)),
    Check("NO-CONCENTRATION-BREACH", "no issuer over its concentration cap", lambda s: not s.get("concentration_breach", True)),
]


def test_standard_from_checks_names_and_versions():
    std = standard_from_checks("SOX-lite", "2026.1", CHECKS)
    assert std["name"] == "SOX-lite" and std["version"] == "2026.1"
    assert len(std["checks"]) == 3


def test_standard_rejects_empty_or_duplicate():
    with pytest.raises(ValueError):
        standard_from_checks("X", "1", [])
    with pytest.raises(ValueError):
        standard_from_checks("X", "1", [CHECKS[0], CHECKS[0]])


def test_run_checks_receipts_every_result_including_gaps():
    state = {"periods_balanced": True, "all_approved": False, "concentration_breach": False}
    results = run_checks(CHECKS, state)
    by = {r["check"]: r for r in results}
    assert by["PERIODS-BALANCED"]["passed"] is True and by["PERIODS-BALANCED"]["gap"] == ""
    assert by["APPROVALS-PRESENT"]["passed"] is False and by["APPROVALS-PRESENT"]["gap"]  # gap receipted, non-empty


def test_a_broken_predicate_is_a_receipted_gap_not_a_crash():
    boom = [Check("BOOM", "explodes", lambda s: 1 / 0)]
    results = run_checks(boom, {})
    assert results[0]["passed"] is False and "errored" in results[0]["gap"]


def test_enforce_refuses_on_first_gap():
    ready_state = {"periods_balanced": True, "all_approved": True, "concentration_breach": False}
    enforce_checks(CHECKS, ready_state)  # no raise
    with pytest.raises(ComplianceGap):
        enforce_checks(CHECKS, {"periods_balanced": True, "all_approved": False, "concentration_breach": False})


def test_audit_readiness_aggregates_gaps():
    results = run_checks(CHECKS, {"periods_balanced": True, "all_approved": False, "concentration_breach": True})
    ar = audit_readiness(results)
    assert ar["ready"] is False and ar["total"] == 3 and ar["passed"] == 1
    assert {g["check"] for g in ar["gaps"]} == {"APPROVALS-PRESENT", "NO-CONCENTRATION-BREACH"}
    # a fully-compliant state is audit-ready
    ar2 = audit_readiness(run_checks(CHECKS, {"periods_balanced": True, "all_approved": True, "concentration_breach": False}))
    assert ar2["ready"] is True and ar2["gaps"] == []
