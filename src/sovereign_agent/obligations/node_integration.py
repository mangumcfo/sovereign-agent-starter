"""Wire the node's real governance into the ObligationLedger (R-23 Phase 2).

This is the SEAM: it adapts the node's HumanApprovalGate + ComplianceEngine into the two
duck-typed callables the ledger expects (`gate`, `attestor`). The pure ledger (ledger.py) has
no node dependency; all node coupling lives here.

  gate(action, obligation)            -> {"status": "approved"|"denied"|"pending", ...}
  attestor(action_class, principal_id, payload, result_summary) -> node audit record (has receipt_hash)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .ledger import ObligationLedger


def make_gate(approval_gate: Any, *, simulate: bool = True, simulate_deny: bool = False,
              approver: str = "Compliance Officer (simulated)") -> Callable:
    """Adapt a node HumanApprovalGate into the ledger's gate-callable.

    simulate=True (dev): routes request → simulate_approval (a stand-in for the human).
      simulate_deny=True forces the simulated human to DENY (for testing the deny path).
    simulate=False (prod): returns 'pending' — real disposition arrives via an external workflow;
    the caller must not treat a material obligation as closeable until that disposition lands.
    """
    from ..compliance.human_approval_gate import ApprovalRequest  # local import (seam)

    def gate(action: str, obligation: Dict) -> Dict:
        req = ApprovalRequest(
            action_class=f"obligation_{action}",
            role_id="obligation_ledger",
            principal_id=str(obligation.get("approved_by", "node")),
            risk_level="high",
            rationale=str(obligation.get("rationale", "")),
            required_approvers=[approver],
        )
        req_id = approval_gate.request_approval(req)
        if not simulate:
            return {"status": "pending", "req_id": req_id,
                    "note": "awaiting external human disposition"}
        if simulate_deny:
            res = approval_gate.simulate_denial(req_id, approver=approver, reason="human denied (test)")
        else:
            res = approval_gate.simulate_approval(req_id, approver=approver)
        return {
            "status": "approved" if res.get("status") == "approved" else "denied",
            "req_id": req_id, "approver": approver,
            "note": "simulated human disposition (dev); production routes to an external approver",
        }

    return gate


def _jsonable(x: Any) -> Any:
    """Coerce a node return (dataclasses/enums/etc.) into JSON-serializable form, since the
    ledger persists NDJSON. Unknown objects fall back to repr (never silently dropped)."""
    import dataclasses
    import json

    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        x = dataclasses.asdict(x)
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    try:
        json.dumps(x)
        return x
    except TypeError:
        return str(x)


def make_attestor(compliance_engine: Any, role_id: str = "obligation_ledger") -> Callable:
    """Adapt a node ComplianceEngine into the ledger's attestor-callable (mints node receipts).
    Normalizes the node's AuditRecord/dict return into a JSON-serializable receipt summary and
    surfaces `receipt_hash` (the USN Merkle root / chain-of-custody anchor)."""
    def attestor(action_class: str, principal_id: str, payload: Dict,
                 result_summary: str) -> Dict:
        rec = compliance_engine.attest_execution(
            role_id=role_id, action_class=action_class,
            principal_id=principal_id, payload=payload, result_summary=result_summary,
        )
        out = _jsonable(rec)
        if not isinstance(out, dict):
            out = {"record": out}
        rh = out.get("receipt_hash") or getattr(rec, "receipt_hash", None)
        if rh is None and isinstance(out.get("usn_attestation"), dict):
            rh = out["usn_attestation"].get("memory_root")
        out["receipt_hash"] = rh
        return out
    return attestor


def wire_node_ledger(root: Optional[str], node: Any, *, mode: str = "sovereign",
                     role_id: str = "obligation_ledger", policy: Optional[Dict] = None,
                     principal_id: str = "node", simulate_gate: bool = True,
                     simulate_deny: bool = False) -> ObligationLedger:
    """Return an ObligationLedger wired to the node's real gate + compliance attestation.

    Honest seam: the ledger's storage root is still node-local (boundary guard applies);
    a material obligation must clear the breath-gate before close; every close mints a
    node receipt via the ComplianceEngine (USN Merkle attestation / SOX-style chain-of-custody).
    """
    from ..compliance.compliance_engine import ComplianceEngine
    from ..compliance.human_approval_gate import HumanApprovalGate

    ce = ComplianceEngine(mode=mode, node=node)
    ag = HumanApprovalGate(policy=policy or {})
    return ObligationLedger(
        root=root, principal_id=principal_id,
        gate=make_gate(ag, simulate=simulate_gate, simulate_deny=simulate_deny),
        attestor=make_attestor(ce, role_id),
    )
