"""Services — a governed professional-services engagement composing sealed project budget (fail-closed), billing
(value-conserving invoice from recorded time), and posting (balanced) for the Professional Services vertical (s5_21)."""
from .engagement import (
    open_engagement, transition, record_time, billable_by_resource, billable_amount,
    budget_position, bill, bill_posting, EngagementError,
)

__all__ = [
    "open_engagement", "transition", "record_time", "billable_by_resource", "billable_amount",
    "budget_position", "bill", "bill_posting", "EngagementError",
]
