"""Engagement — a governed professional-services engagement composing the sealed project, billing, and posting surfaces.

Co-extrusion for s5_21 (Professional Services, KM 2026-08-04). Pure / structural, no crypto substrate (F-1
pure-clone-clean). A professional-services firm does not re-implement projects, payroll, or invoicing: this vertical
composes the sealed primitives into one governed billing act -- an engagement that turns recorded time on a client
project into a value-conserving invoice, fail-closed on the project budget. An engagement carries a governed rate card
(a billing rate per resource -- the resources being the governed people the sealed human-capital surface governs); time
is recorded against it by resource and task, value-conserving -- a resource not on the rate card, or a non-positive
hour, is refused; the billable amount is the recorded hours at their rates, conserved exactly; billing is fail-closed on
the project budget (an engagement over its governed budget cannot bill without a governed override -- composing the
sealed project-budget position); the bill is a value-conserving invoice built from the recorded hours (composing the
sealed invoice); and the sale posts accounts receivable against services revenue as a balanced {debits, credits} entry
that composes the sealed general ledger via financials.posting.from_entry. Human primacy holds: the engagement is
opened, its time approved, and its budget overridden by governed acts; this module holds the discipline and refuses what
would break it -- billing time never recorded, or beyond the governed budget. The project and task structure the
engagement runs against is the sealed project surface, composed here, not rebuilt."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Tuple, Union

from ..revenue.billing import invoice as _invoice
from ..financials.project import budget_status as _budget_status

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")

# Engagement lifecycle -- fail-closed transitions (added to docs/DOMAIN_VOCAB_CARD.md per spine item 8).
_ENG_ALLOWED: Dict[str, set] = {
    "open": {"active", "cancelled"},
    "active": {"billed", "cancelled"},
    "billed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class EngagementError(ValueError):
    """Raised for an illegal lifecycle transition, time recorded for a resource not on the rate card or at a
    non-positive hour, or a bill that would exceed the governed project budget -- fail-closed, never a silent overrun."""


def open_engagement(engagement_id: str, client: str, rate_card: Mapping[str, Number],
                    budget: Number) -> Dict[str, object]:
    """Open an engagement for a client against a governed budget, with a rate card (a billing rate per resource -- the
    resources being the governed people the sealed human-capital surface governs). Starts `open` with no time recorded.
    Refuses an empty rate card or a negative budget."""
    if not rate_card:
        raise EngagementError("engagement needs a rate card (a rate per resource)")
    rc = {r: _dec(v) for r, v in rate_card.items()}
    for r, v in rc.items():
        if v < 0:
            raise EngagementError(f"rate for resource {r!r} must be >= 0 (got {v})")
    if _dec(budget) < 0:
        raise EngagementError(f"budget must be >= 0 (got {budget})")
    return {"id": engagement_id, "client": client, "rate_card": rc, "budget": _dec(budget),
            "entries": [], "status": "open"}


def transition(engagement: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move an engagement to `to_status`, fail-closed: the lifecycle must permit the move (you cannot bill an engagement
    that recorded no time and went active, or reopen a closed one). Returns (new_engagement, event); input not mutated."""
    frm = engagement.get("status", "open")
    if to_status not in _ENG_ALLOWED.get(frm, set()):
        raise EngagementError(f"engagement {engagement.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                              f"(allowed from {frm!r}: {sorted(_ENG_ALLOWED.get(frm, set())) or 'none'})")
    ne = dict(engagement)
    ne["status"] = to_status
    return ne, {"engagement": engagement.get("id"), "from": frm, "to": to_status}


def record_time(engagement: Mapping, entries: Sequence[Mapping]) -> Dict[str, object]:
    """Record time entries against the engagement, value-conserving: each entry names a `resource` (on the rate card), a
    `task`, and positive `hours`. A resource not on the rate card, or a non-positive hour, is refused -- time cannot be
    recorded for someone with no governed rate, or as zero. Returns the updated engagement (status open -> active);
    input not mutated."""
    if engagement.get("status") not in ("open", "active"):
        raise EngagementError(f"engagement {engagement.get('id')!r}: cannot record time on a "
                              f"{engagement.get('status')!r} engagement")
    rc = engagement["rate_card"]
    new_entries = list(engagement.get("entries", []))
    for e in entries:
        r, hrs = e["resource"], _dec(e["hours"])
        if r not in rc:
            raise EngagementError(f"engagement {engagement.get('id')!r}: resource {r!r} is not on the rate card")
        if hrs <= 0:
            raise EngagementError(f"engagement {engagement.get('id')!r}: hours for {r!r} must be > 0 (got {hrs})")
        new_entries.append({"resource": r, "task": e.get("task"), "hours": hrs})
    ne = dict(engagement)
    ne["entries"] = new_entries
    ne["status"] = "active"
    return ne


def billable_by_resource(engagement: Mapping) -> Dict[str, Dict[str, Decimal]]:
    """Aggregate recorded time by resource: total hours and the billable amount (hours at the rate-card rate)."""
    rc = engagement["rate_card"]
    agg: Dict[str, Dict[str, Decimal]] = {}
    for e in engagement.get("entries", []):
        r = e["resource"]
        cur = agg.setdefault(r, {"hours": Decimal("0"), "amount": Decimal("0")})
        cur["hours"] += _dec(e["hours"])
        cur["amount"] = (cur["hours"] * rc[r]).quantize(_CENTS)
    return agg


def billable_amount(engagement: Mapping) -> Decimal:
    """The engagement's billable amount: the sum over resources of recorded hours at their rate-card rates."""
    return sum((v["amount"] for v in billable_by_resource(engagement).values()), Decimal("0")).quantize(_CENTS)


def budget_position(engagement: Mapping) -> Dict[str, object]:
    """The engagement's budget position against its governed budget, composing the sealed project-budget surface: the
    billable amount is the actual consumed, and the position reports whether the engagement is over budget."""
    return _budget_status(engagement["budget"], 0, billable_amount(engagement))


def bill(engagement: Mapping, tax: Number = 0, currency: str = "USD") -> Dict[str, object]:
    """Bill the engagement, fail-closed on the governed project budget: an engagement whose billable amount exceeds its
    budget cannot bill (an override is a governed act), and the invoice is value-conserving -- one line per resource
    (the recorded hours at the rate-card rate), composing the sealed invoice, so the bill conserves exactly to the
    recorded time. Only an active engagement may be billed."""
    if engagement.get("status") != "active":
        raise EngagementError(f"engagement {engagement.get('id')!r}: only an active engagement can be billed "
                              f"(is {engagement.get('status')!r})")
    pos = budget_position(engagement)
    if pos["over_budget"]:
        raise EngagementError(f"engagement {engagement.get('id')!r}: billable {billable_amount(engagement)} exceeds "
                              f"the governed budget {engagement['budget']} (overrun {pos['overrun']}) -- billing "
                              "refused; an override is a governed act")
    lines = [{"description": r, "quantity": v["hours"], "unit_price": engagement["rate_card"][r]}
             for r, v in billable_by_resource(engagement).items()]
    return _invoice(lines, tax=tax, currency=currency)


def bill_posting(engagement: Mapping, tax: Number = 0, ar_account: str = "accounts receivable",
                 revenue_account: str = "services revenue", tax_account: str = "sales tax payable") -> Dict[str, object]:
    """The engagement's bill as a value-conserving, balanced posting in the {debits, credits} shape: accounts
    receivable is debited the invoice total, services revenue is credited the subtotal, and the named tax is credited to
    tax payable -- so debits equal credits by construction. Posts to the sealed general ledger via
    financials.posting.from_entry."""
    inv = bill(engagement, tax=tax)
    subtotal, t, total = inv["subtotal"], inv["tax"], inv["total"]
    credits = [{"account": revenue_account, "amount": subtotal}]
    if t > 0:
        credits.append({"account": tax_account, "amount": t})
    return {"engagement_id": engagement.get("id"), "debits": [{"account": ar_account, "amount": total}],
            "credits": credits, "balanced": total == subtotal + t, "amount": total}
