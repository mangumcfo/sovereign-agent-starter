"""
HumanApprovalGate + EscalationPolicy — lightweight, sovereign, configurable.

Designed to be used by ComplianceEngine and BoundRole in corporate_regulated mode.
Can be simulated (demos) or wired to real ticketing / approval systems.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"


@dataclass
class ApprovalRequest:
    action_class: str
    role_id: str
    principal_id: str
    risk_level: str
    rationale: str
    required_approvers: List[str]


class HumanApprovalGate:
    """
    Simple but effective human oversight gate.
    In regulated corporate mode, high-risk or Charter V.7-adjacent actions
    can be forced through this gate before the handler is invoked.
    """

    def __init__(self, policy: Optional[Dict] = None):
        self.policy = policy or {}
        self._pending: Dict[str, ApprovalRequest] = {}
        # Monotonic req_id counter (audit 2026-07-08 AH-6). Deriving the id from len(self._pending)
        # reused a live id after any disposition popped the queue — a later request could clobber a
        # still-pending one. A never-decrementing sequence makes every minted req_id unique for the
        # process lifetime, so no pending request is ever silently overwritten.
        self._seq = 0

    def requires_approval(self, action_class: str, role_spec: Dict, mode: str) -> bool:
        if mode != "corporate_regulated":
            return False
        forbidden = role_spec.get("charter_v7_forbidden_classes", [])
        if action_class in forbidden:
            return True
        high_materiality = self.policy.get("high_materiality_classes", [])
        return action_class in high_materiality

    def request_approval(self, req: ApprovalRequest) -> str:
        self._seq += 1
        req_id = f"approval_{self._seq}"
        self._pending[req_id] = req
        return req_id

    def simulate_approval(self, req_id: str, approver: str = "Compliance Officer (simulated)") -> Dict:
        """TEST-ONLY stand-in (audit 2026-06-16 #4b). The live /breath_gate/<id>/approve route records a
        REAL disposition via record_disposition(); this simulated path is for tests/demos only."""
        if req_id not in self._pending:
            return {"status": "unknown_request"}
        # In a real system this would be an external workflow callback
        self._pending.pop(req_id, None)  # leaves the pending queue once disposed
        return {
            "status": "approved",
            "req_id": req_id,
            "approver": approver,
            "timestamp": "simulated",
            "note": "Human judgment recorded. Action may proceed.",
        }

    def simulate_denial(self, req_id: str, approver: str = "Compliance Officer (simulated)", reason: str = "") -> Dict:
        """TEST-ONLY stand-in (audit 2026-06-16 #4b), symmetric to simulate_approval — an explicit human DENY.
        The live /breath_gate/<id>/deny route records a REAL disposition via record_disposition()."""
        if req_id not in self._pending:
            return {"status": "unknown_request"}
        self._pending.pop(req_id, None)  # leaves the pending queue once disposed
        return {
            "status": "denied",
            "req_id": req_id,
            "approver": approver,
            "reason": reason or "Human judgment recorded. Action refused.",
            "timestamp": "simulated",
            "note": "Action did not proceed. The refusal is the constitutional act.",
        }

    def record_disposition(self, req_id: str, status: str = "approved",
                           approver: str = "node", reason: str = "") -> Dict:
        """Record a REAL human disposition — the authenticated principal who acted at the breath-gate
        (the /approve endpoint, behind require_principal). Not a simulation: a real actor + a real UTC
        timestamp (audit 2026-06-11, real_gates_every_mode). simulate_approval / simulate_denial above
        remain TEST-ONLY stand-ins and are never used in the live wiring."""
        from datetime import datetime, timezone  # noqa: PLC0415
        if req_id not in self._pending:
            return {"status": "unknown_request"}
        self._pending.pop(req_id, None)
        return {
            "status": status, "req_id": req_id, "approver": approver, "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(), "real": True,
            "note": "Human judgment recorded by the authenticated principal.",
        }

    def get_pending(self) -> Dict[str, ApprovalRequest]:
        return dict(self._pending)
