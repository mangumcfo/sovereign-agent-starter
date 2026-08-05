"""Console — the Sovereign ERP Operations Console (s5_32): the operator SHELL. It BINDS the sealed operational
surfaces (the human-approval gate and the exception primitive) into ONE operator view and ONE dispatch point —
a projection and a router, NOT a second cockpit engine and NOT a second approval system. It holds no state and no
authority of its own: the inbox decomposes to the surfaces beneath it, and every dispatched intent is handled by
the sealed gate/primitive that owns it."""
from .operations import operator_inbox, dispatch, ConsoleError

__all__ = ["operator_inbox", "dispatch", "ConsoleError"]
