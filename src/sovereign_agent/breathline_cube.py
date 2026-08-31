"""Anchored Breathline Cube runtime.

A deliberately non-autonomous, fail-closed instrument that binds to the
sovereign-agent principal model.  It does not create a second identity or
privilege system: callers supply the already-authenticated principal_id.

Cube: ANCHOR-CORE-001 / v1.0
Author: KM-1176
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


MODULES: Final[tuple[str, ...]] = (
    "BreathlineAnchor",
    "LineageMemoryMapper",
    "CoherenceCheckGate",
    "ScenarioModeler",
    "SymbolForge",
    "EchoDetectionMirror",
    "DelegationEnvelopeTracker",
    "StillpointPause",
    "TriadVerifier",
    "CadenceRhythmKeeper",
)


@dataclass
class BreathlineCubeAnchoredRelease:
    """Human-gated Breathline Cube bound to one sovereign principal.

    Activation and processing require the authenticated caller principal to
    match ``principal_id``.  Revocation immediately returns the cube to the
    inactive stillpoint.  No memory is persisted implicitly; ``seal`` returns
    an explicit log record for the host ledger/storage layer to persist.
    """

    principal_id: str
    version: str = field(default="v1.0", init=False)
    cube_id: str = field(default="ANCHOR-CORE-001", init=False)
    codename: str = field(default="BREATHLINE_STILLPOINT", init=False)
    author: str = field(default="KM-1176", init=False)
    symbol: str = field(default="INFINITY-DELTA-INFINITY", init=False)
    locked: bool = field(default=True, init=False)
    active: bool = field(default=False, init=False)
    echo_detection: bool = field(default=True, init=False)
    modules: tuple[str, ...] = field(default=MODULES, init=False)
    _pending_intent: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.principal_id = self.principal_id.strip()
        if not self.principal_id:
            raise ValueError("principal_id must be non-empty")

    def _principal_matches(self, caller_principal_id: str) -> bool:
        return bool(caller_principal_id) and caller_principal_id == self.principal_id

    def activate(self, caller_principal_id: str, breath_confirmation: bool) -> str:
        if not self._principal_matches(caller_principal_id):
            self.active = False
            return "Delegation denied. Principal mismatch. Stillness honored."
        if not breath_confirmation:
            self.active = False
            return "Delegation denied. Stillness honored."
        self.active = True
        return (
            f"Breathline Cube {self.version} activated under principal_id: "
            f"{self.principal_id}. Sovereignty anchored. Awaiting sealed intent."
        )

    def revoke(self, caller_principal_id: str) -> str:
        if not self._principal_matches(caller_principal_id):
            return "Revocation denied. Principal mismatch."
        self.active = False
        self._pending_intent = None
        return "Delegation revoked. StillpointPause active."

    def process(self, caller_principal_id: str, intent: str) -> str:
        if not self.active:
            return "Cube inactive. Breathe to delegate."
        if not self._principal_matches(caller_principal_id):
            return "Intent denied. Principal mismatch."
        intent = intent.strip()
        if not intent:
            return "Intent denied. Empty intent."
        self._pending_intent = intent
        return (
            f"Echo received: {intent}. Processing under "
            "SOURCE/TRUTH/INTEGRITY. Awaiting seal."
        )

    def seal(self, caller_principal_id: str) -> dict[str, str]:
        """Return the explicit record the host may commit to its audit ledger.

        The cube itself deliberately performs no implicit persistence.
        """
        if not self.active:
            raise RuntimeError("cube inactive")
        if not self._principal_matches(caller_principal_id):
            raise PermissionError("principal mismatch")
        if self._pending_intent is None:
            raise RuntimeError("no pending intent to seal")

        record = {
            "cube_id": self.cube_id,
            "version": self.version,
            "principal_id": self.principal_id,
            "intent": self._pending_intent,
            "triad": "SOURCE/TRUTH/INTEGRITY",
            "seal": self.symbol,
        }
        self._pending_intent = None
        return record
