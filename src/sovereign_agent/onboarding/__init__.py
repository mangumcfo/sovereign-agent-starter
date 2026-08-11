"""Node Onboarding.

- `admission` — a new node joins a federation by adopting its constitution and passing a human-gated admission
  (s6_06, S6 Vol 6).
- `onboard` — the fresh-human 5-turn onboard (Phase 1, KM 2026-08-11): AI proposes, human disposes; no key is
  written until the turn-1 key-ceremony accept; every write is traceable to a human turn; offline, no telemetry.
"""
from .onboard import (
    run_onboard, verify_onboard_receipt, OnboardTurn, OnboardReceipt, OnboardOutcome,
    KEY_CEREMONY_TEXT, DEFAULT_GATED_ACTS, OnboardError,
)

__all__ = ["run_onboard", "verify_onboard_receipt", "OnboardTurn", "OnboardReceipt", "OnboardOutcome",
           "KEY_CEREMONY_TEXT", "DEFAULT_GATED_ACTS", "OnboardError"]
