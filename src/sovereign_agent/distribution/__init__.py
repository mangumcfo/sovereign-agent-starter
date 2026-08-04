"""Distribution — a governed sales-order fulfillment composing sealed inventory (fail-closed allocation), billing
(value-conserving invoice), credit (fail-closed gate), and posting (balanced sale) for the Distribution & Wholesale
vertical (s5_20)."""
from .fulfillment import (
    open_sales_order, transition, allocate, credit_check, order_subtotal,
    invoice_shipment, sale_posting, FulfillmentError,
)

__all__ = [
    "open_sales_order", "transition", "allocate", "credit_check", "order_subtotal",
    "invoice_shipment", "sale_posting", "FulfillmentError",
]
