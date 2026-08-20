"""Revenue — value-conserving recognition, governed order-to-invoice billing + AR aging, and fail-closed credit (s5_15)."""
from .recognition import recognize, POINT_IN_TIME, RATABLE, MILESTONE, RecognitionError
from .billing import invoice, ar_aging, BillingError
from .credit import check_order, available_credit, CreditError
from .cash_application import (
    receipt, apply, reverse, replay_state, aging_rows, CashApplicationError,
)

__all__ = [
    "recognize", "POINT_IN_TIME", "RATABLE", "MILESTONE", "RecognitionError",
    "invoice", "ar_aging", "BillingError",
    "check_order", "available_credit", "CreditError",
    "receipt", "apply", "reverse", "replay_state", "aging_rows", "CashApplicationError",
]
