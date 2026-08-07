# -*- coding: utf-8 -*-
"""sovereign_ux.cockpit — Atrium as Living OS (S8 Vol 4).

`compose_cockpit` assembles the operator's **host decision surface** by COMPOSING the operator-layer
volumes and the sealed floors — it owns nothing, hosts nothing, and holds no authority of its own:

  * **render** a governed object through the **governed token set** (V03 `apply_tokens`, which composes
    the V01 Lens) — the flagship surface renders through the governed aesthetic, read-only and honest.
  * **propose / dispose** an action **only through the V02 breath-gate** (`gate_interaction`) — the
    cockpit has NO direct write path; every state change is a human-gated, mandate-scoped disposition
    in the ledger-backed constitutional gate.
  * **lgp_watch** — render the node's economic-value state (from `yield_organism`) **READ-ONLY**: it
    DISPLAYS the objective (amm-pool state, payout schedule, recirculation allocation), and never runs
    or optimizes the engines. Display only.

Kill-targets: **composes, never owns** — no hosted control plane, no second authority, writes only
through V02's gate, and **LGP Watch displays the objective, never optimizes it autonomously.** Books
`playbook_loader` (the inbox) and `universal_sovereign_node` (the core) at their first home. Composes
V01 Lens · V02 Breath-Gate · V03 apply_tokens · `yield_organism` (read-only) · Compliance & Audit
(S5 Vol 16, via the gate) · the mandate scope (S5 Vol 28, via the Lens). **Rolls no cryptography.**
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .lens import View                                   # V01 (via V03)
from .tokens import TokenSet, apply_tokens               # V03 The Governed Aesthetic (composes V01)
from .gate_interaction import propose, review, dispose   # V02 Breath-Gated Interfaces (the write path)

__all__ = ["Cockpit", "compose_cockpit"]


@dataclass(frozen=True)
class Cockpit:
    """The host decision surface. A frozen composition — it holds references to the node's governed
    token set and (optionally) its obligation ledger, and offers rendering + the gated write path +
    the read-only LGP Watch. It exposes NO method that mutates a governed object directly."""
    token_set: TokenSet
    ledger: Any = None  # the node's ObligationLedger; required for the write path (propose/dispose)

    # ── render: through the governed token set (V03 → V01), read-only + honest ──────────────────
    def render(self, obj: Any, *, mandate: Optional[str] = None,
               scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
        """Render a governed object through the governed aesthetic — `apply_tokens` (V03), which
        composes the Sovereign Lens (V01): read-only, honest, mandate-scoped, off-token refused."""
        return apply_tokens(obj, self.token_set, mandate=mandate, scope=scope)

    # ── write: ONLY through the V02 breath-gate ─────────────────────────────────────────────────
    def propose(self, title: str, **kw) -> str:
        """Propose an action — a DRAFT obligation, applied by nothing (V02 `propose`)."""
        return propose(self._require_ledger(), title, **kw)

    def pending(self) -> list:
        """The ledger-backed pending dispositions (V02 `review`) — the constitutional truth."""
        return review(self._require_ledger())

    def dispose(self, obligation_id: str, **kw) -> dict:
        """Dispose of a proposal — the human breath-gate, mandate-scoped (V02 `dispose`). The cockpit
        holds no authority to approve; the write is the core's, on a human's recorded assent."""
        return dispose(self._require_ledger(), obligation_id, **kw)

    # ── LGP Watch: render the economic-value state READ-ONLY; never run or optimize ─────────────
    def lgp_watch(self, yield_state: Mapping[str, Any], *, mandate: Optional[str] = None) -> View:
        """Render a READ-ONLY snapshot of the node's economic-value state (from `yield_organism` —
        amm-pool state, payout schedule, recirculation allocation) through the governed tokens.

        The caller supplies the state snapshot; the cockpit **renders** it and returns a read-only
        Lens View. It DISPLAYS the objective; it does not run the AMM, execute a payout, or optimize
        anything — there is no path here that invokes a `yield_organism` engine.
        """
        return apply_tokens(dict(yield_state), self.token_set, mandate=mandate)

    def _require_ledger(self):
        if self.ledger is None:
            raise ValueError("cockpit write path requires the node's obligation ledger — "
                             "the cockpit writes only through the V02 breath-gate, never directly")
        return self.ledger


def compose_cockpit(*, token_set: TokenSet, ledger: Any = None) -> Cockpit:
    """Compose the operator's host decision surface from the node's governed token set and (for the
    write path) its obligation ledger. The cockpit composes; it owns nothing."""
    return Cockpit(token_set=token_set, ledger=ledger)
