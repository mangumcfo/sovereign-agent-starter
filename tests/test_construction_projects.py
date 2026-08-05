"""Acceptance tests for the Construction vertical (s5_23, Vol 25) — a governed construction job composing the sealed
project-budget + revenue billing + compliance human-gate + posting. Pure / structural (F-1 clean)."""
from decimal import Decimal

import pytest

from sovereign_agent.construction.projects import (
    open_job, commit_subcontract, certify_progress, ConstructionError,
)


def test_open_job_refuses_nonpositive_budget():
    with pytest.raises(ConstructionError):
        open_job("JOB-1", 0)
    with pytest.raises(ConstructionError):
        open_job("", 100)


def test_commit_subcontract_records_within_budget():
    job = open_job("JOB-1", 100_000)
    j2 = commit_subcontract(job, "Ace Electrical", 40_000)
    assert j2["committed"] == Decimal("40000")
    assert j2["budget_status"]["over_budget"] is False
    assert j2["subcontracts"][0]["subcontractor"] == "Ace Electrical"
    assert job["committed"] == Decimal("0")  # input not mutated


def test_commit_subcontract_refuses_over_budget():
    job = commit_subcontract(open_job("JOB-1", 100_000), "Ace Electrical", 80_000)
    with pytest.raises(ConstructionError):
        commit_subcontract(job, "Beam Steel", 30_000)  # 110k > 100k governed budget


def test_certify_progress_bills_balanced_with_named_human():
    job = open_job("JOB-1", 100_000)
    res = certify_progress(
        job,
        [{"description": "foundation 30%", "quantity": 1, "unit_price": 30_000}],
        approver="site-super", approval_ref="cert #7 signed 2026-08",
    )
    assert res["certified"] is True
    p = res["posting"]
    assert p["balanced"] is True
    assert sum(Decimal(l["debit"]) for l in p["lines"]) == sum(Decimal(l["credit"]) for l in p["lines"]) == Decimal("30000")


def test_certify_progress_refuses_without_named_approver_or_ref():
    job = open_job("JOB-1", 100_000)
    lines = [{"description": "foundation", "quantity": 1, "unit_price": 1000}]
    with pytest.raises(ConstructionError):
        certify_progress(job, lines, approver="  ", approval_ref="cert signed")
    with pytest.raises(ConstructionError):
        certify_progress(job, lines, approver="site-super", approval_ref="")


def test_certify_progress_refuses_nonexistent_job():
    with pytest.raises(ConstructionError):
        certify_progress({}, [{"description": "x", "quantity": 1, "unit_price": 1}],
                         approver="site-super", approval_ref="cert signed")
