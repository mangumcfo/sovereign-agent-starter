"""Governance — exception & governance workflows at scale (s5_29): a governed exception primitive that ROUTES an
exception to the right human gate and RESOLVES it fail-closed, composing the sealed gates (the human-approval gate and
the GRC case lifecycle, Compliance & Audit; the mandate authorization, Structural SoD & Access Governance) rather than
building a second approval system. It adds the routing and the resolution lifecycle over the sealed gates -- not a new
gate."""
from .exception import (
    open_exception, route, resolve, route_batch, ExceptionError,
)

__all__ = ["open_exception", "route", "resolve", "route_batch", "ExceptionError"]
