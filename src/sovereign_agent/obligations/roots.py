"""Ledger-root resolution + the hard boundary against the live seal chain — extracted verbatim from
ledger.py (audit 2026-06-16 #6). `get_ledger_root` is the ONE resolver every node-side site routes
through. Re-exported by ledger.py for back-compat. Path(__file__).parents[3] is unchanged: this module
lives in the SAME obligations/ dir as ledger.py, so it resolves to the same repo root."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class LedgerBoundaryError(RuntimeError):
    """Raised if the ledger root would land inside the protected live cylinder infra."""


# Substrings that must never appear in a resolved ledger root (the live Tiger seal chain).
FORBIDDEN_ROOT_FRAGMENTS = (os.path.join("Tiger_1a", "cylinders"),)

ENV_ROOT = "OBLIGATION_LEDGER_ROOT"


def _default_root() -> Path:
    # roots.py -> obligations -> sovereign_agent -> src -> <repo root>
    repo = Path(__file__).resolve().parents[3]
    return repo / "memory" / "obligations"


def _node_default_root() -> Path:
    """The node's canonical ledger root: the live review queue (memory/obligations/atrium_review), where
    the real cards live. The ONE default every node-side reader/writer falls back to when the env is
    unset — so an env-unset API serves the real chain instead of an empty parent path."""
    return _default_root() / "atrium_review"


def _resolve_root(root: Optional[os.PathLike | str]) -> Path:
    if root is None:
        root = os.environ.get(ENV_ROOT)
    # ONE default (audit 2026-06-13d #12): a bare ObligationLedger() (no root, no env) resolves to the
    # node canonical root (atrium_review, where the cards live) — NOT the empty parent. The empty-parent
    # default was the "starved root" split-brain (a bare constructor served an empty chain beside the rich
    # sibling), the exact bug that once hid KM's cards; the raw constructor never runs deps' starve-guard.
    p = Path(root).expanduser().resolve() if root else _node_default_root().resolve()
    s = str(p)
    for frag in FORBIDDEN_ROOT_FRAGMENTS:
        if frag in s:
            raise LedgerBoundaryError(
                f"ObligationLedger refuses root '{s}': it is inside the protected live "
                f"cylinder infra ('{frag}'). The node must never write the live seal chain. "
                f"Set {ENV_ROOT} to a node-local path."
            )
    return p


def get_ledger_root(explicit: Optional[os.PathLike | str] = None,
                    default: Optional[os.PathLike | str] = None) -> Path:
    """THE single ledger-root resolver (audit 2026-06-13). Resolution order:
        explicit arg → OBLIGATION_LEDGER_ROOT env → caller `default` → node canonical (atrium_review).
    Every node-side site (API deps, bell executor, /export, /actions, review_ready) routes through this
    so the API and the bell executor can NEVER resolve different roots — the split-brain that landed
    approve in one chain and close in another. Boundary-checked exactly like _resolve_root."""
    chosen = explicit or os.environ.get(ENV_ROOT) or default or _node_default_root()
    return _resolve_root(chosen)
