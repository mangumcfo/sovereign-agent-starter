"""Construction projects — a governed construction job composing the sealed project-budget, revenue, and posting surfaces.

Co-extrusion for s5_23 (Construction & Projects, KM Verticals wave 2026-08-05). Pure / structural, no crypto substrate
(F-1 pure-clone-clean). A general contractor does not re-implement job costing, the project ledger, progress invoicing,
or the human sign-off: this vertical composes the sealed primitives into one governed construction job -- a job costed
against a governed budget, whose subcontractor commitments are fail-closed against that budget (no silent overrun), and
whose progress is certified only through a human gate before it can bill.

Two governed acts:
  * `commit_subcontract` records a subcontractor commitment on a governed job, fail-closed against the job's budget --
    composing the sealed project-budget position (`financials.project.budget_status`); a commitment that would carry the
    job over its governed budget is refused, so a job is never over-committed silently;
  * `certify_progress` is DENY-BY-DEFAULT, fail-closed, in order: the job must be a real governed job, a progress
    certification must be a human-gated action class (composing the sealed `HumanApprovalGate` -- a construction progress
    claim, carrying the safety sign-off, is high-materiality), and a NAMED human (the site superintendent) must approve
    (an approver and a non-empty approval reference naming the certification); only then does the certified progress bill,
    its invoice composing the sealed revenue surface (`revenue.billing.invoice`) and posting to the sealed general ledger
    as a balanced {debits, credits} entry via financials.posting.from_entry.

Human primacy holds: the budget is governed, the commitments are fail-closed against it, and progress bills only after a
named human certifies it. This module holds the discipline and refuses what would break it -- a commitment beyond the
governed budget, or a progress bill with no certified, named human's assent. Nothing here is a new job-costing engine,
project ledger, billing engine, or approval engine; each is the sealed floor, composed."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

from ..financials.project import budget_status
from ..revenue.billing import invoice as _invoice
from ..financials.posting import from_entry
from ..compliance.human_approval_gate import HumanApprovalGate

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ConstructionError(ValueError):
    """Raised when a construction job cannot proceed honestly: a non-positive budget, a subcontractor commitment that
    would carry the job over its governed budget, or a progress certification without a real job, without the human-gated
    class, or without a named human's assent -- fail-closed, never a silent budget overrun or an uncertified progress bill."""


def open_job(job_id: str, budget: Number, *, currency: str = "USD") -> Dict[str, object]:
    """Open a governed construction job against a budget, with nothing committed or spent. Refuses an empty id or a
    non-positive budget."""
    if not job_id:
        raise ConstructionError("job needs an id")
    b = _dec(budget)
    if b <= 0:
        raise ConstructionError(f"job budget must be > 0 (got {b})")
    return {"id": job_id, "budget": b, "committed": _dec(0), "actual": _dec(0),
            "currency": currency, "status": "open", "subcontracts": []}


def commit_subcontract(job: Mapping, subcontractor: str, amount: Number, memo: str = "") -> Dict[str, object]:
    """Record a subcontractor commitment on a governed job, fail-closed against the job's budget -- composing the sealed
    project-budget position. The new committed total is tested with `financials.project.budget_status`; if the job would
    go over its governed budget, the commitment is refused (no silent overrun -- a real over-budget position, not a
    hopeful projection). Returns a new job with the commitment recorded; the input is not mutated."""
    amt = _dec(amount)
    if not str(subcontractor).strip():
        raise ConstructionError("a subcontractor commitment needs a named subcontractor")
    if amt <= 0:
        raise ConstructionError(f"commitment amount must be > 0 (got {amt})")
    new_committed = _dec(job.get("committed", 0)) + amt
    status = budget_status(job["budget"], new_committed, job.get("actual", 0))
    if status["over_budget"]:
        raise ConstructionError(
            f"subcontract refused: commitment of {amt} would carry job {job['id']!r} over its governed budget "
            f"(overrun {status['overrun']}) -- no silent budget overrun"
        )
    nj = dict(job)
    nj["committed"] = new_committed
    nj["subcontracts"] = list(job.get("subcontracts", [])) + [{"subcontractor": subcontractor, "amount": amt, "memo": memo}]
    nj["budget_status"] = status
    return nj


def certify_progress(job: Mapping, progress_lines: Sequence[Mapping], *, approver: str, approval_ref: str,
                     gate: HumanApprovalGate = None, tax: Number = 0,
                     ar_account: str = "accounts receivable",
                     revenue_account: str = "construction revenue",
                     tax_account: str = "sales tax payable") -> Dict[str, object]:
    """Certify construction progress and bill it -- DENY-BY-DEFAULT, fail-closed, on conditions in order:

      1. the `job` must be a real governed job -- carrying an id and a budget; a certification of nothing is refused;
      2. a progress certification must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate`
         (deny-by-default: a construction progress claim, carrying the safety sign-off, is high-materiality);
      3. a NAMED human (the site superintendent) must approve -- an `approver` and a non-empty `approval_ref` naming the
         certification; a certification with no named approver or no approval reference is refused.

    Only when the job is real AND the class is gated AND a human has certified does the progress bill: its invoice
    composes the sealed revenue surface (`revenue.billing.invoice`, value-conserving from the progress lines) and posts
    to the sealed general ledger as a balanced {debits, credits} entry (accounts receivable debited the total,
    construction revenue credited the subtotal, tax credited to tax payable) via financials.posting.from_entry. The
    project ledger, the billing invariant, the gating policy, and the posting invariant are the sealed floors'; this adds
    only the fail-closed binding -- a real job AND a certified, named human, or no progress bill."""
    if not (job and job.get("id") and job.get("budget") is not None):
        raise ConstructionError("certification refused: no real governed job to certify")
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["progress_certification"]})
    if not gate.requires_approval(
        "progress_certification",
        {"charter_v7_forbidden_classes": ["progress_certification"]},
        "corporate_regulated",
    ):
        raise ConstructionError(
            "certification refused: a progress certification must be a human-gated action class (deny-by-default)"
        )
    if not str(approver).strip():
        raise ConstructionError("certification refused: a named human approver (site superintendent) is required")
    if not str(approval_ref).strip():
        raise ConstructionError("certification refused: an approval reference naming the certification is required")
    inv = _invoice(progress_lines, tax=tax, currency=job.get("currency", "USD"))
    subtotal, t, total = inv["subtotal"], inv["tax"], inv["total"]
    credits = [{"account": revenue_account, "amount": subtotal}]
    if t > 0:
        credits.append({"account": tax_account, "amount": t})
    posting = from_entry(
        {"debits": [{"account": ar_account, "amount": total}], "credits": credits},
        memo=f"certified progress on job {job['id']}",
    )
    return {"certified": True, "job": job["id"], "invoice": inv, "posting": posting,
            "approver": approver, "approval_ref": approval_ref}
