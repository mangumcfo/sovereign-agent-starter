"""GRC-workflow invariants — co-extrusion for s5_14 (Option B+).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the ordered compliance
case (open→evidence→checks→package→sign-off): steps complete in order with an approver, out-of-order refused, and the
hard close (sign-off) refused unless every step is done, an approver is named, and the checks show no open gap."""
import pytest

from sovereign_agent.compliance.grc_workflow import new_case, advance, hard_close, GRCError, STEPS
from sovereign_agent.compliance.audit_checks import Check, run_checks

CHECKS = [Check("BALANCED", "period balances", lambda s: s.get("balanced", False))]


def _walk_to_signoff(case, approver="KM-1176"):
    for step in STEPS:  # open, evidence, checks, package (sign-off is the hard close)
        case = advance(case, step, approver)
    return case


def test_new_case_has_ordered_steps():
    c = new_case("AUDIT-2026Q3")
    assert c["state"] == "open" and c["steps"] == list(STEPS) and c["done"] == []


def test_steps_must_complete_in_order_with_approver():
    c = new_case("C1")
    c = advance(c, "open", "KM-1176")
    assert c["done"] == ["open"]
    with pytest.raises(GRCError):
        advance(c, "checks", "KM-1176")     # out of order (evidence is next)
    with pytest.raises(GRCError):
        advance(c, "evidence", "")          # missing approver


def test_hard_close_refused_until_all_steps_done():
    c = new_case("C2")
    c = advance(c, "open", "KM-1176")
    ready = run_checks(CHECKS, {"balanced": True})
    with pytest.raises(GRCError):
        hard_close(c, ready, "KM-1176")     # steps remaining


def test_open_gap_blocks_hard_close():
    c = _walk_to_signoff(new_case("C3"))
    gap = run_checks(CHECKS, {"balanced": False})   # a failing check
    with pytest.raises(GRCError):
        hard_close(c, gap, "KM-1176")


def test_sign_off_succeeds_when_complete_and_no_gap():
    c = _walk_to_signoff(new_case("C4"))
    ready = run_checks(CHECKS, {"balanced": True})
    closed = hard_close(c, ready, approver="KM-1176")
    assert closed["state"] == "closed" and closed["signed_off"] is True and closed["approver"] == "KM-1176"
    with pytest.raises(GRCError):                    # missing approver refused
        hard_close(c, ready, "")
