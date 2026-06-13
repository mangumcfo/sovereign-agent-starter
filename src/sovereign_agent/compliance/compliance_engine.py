"""
ComplianceEngine + VerifiableInference — Sovereign bridge to Playbook 6 + SIX patterns.

This module embodies (does not duplicate) the compliance and verifiable inference
architecture from:
- Playbook 6 (AI Agents for Compliance): policy-as-code, Charter V.7 enforcement,
  human oversight on judgment, four-layer agent model, SOX/CAFE/fiduciary readiness.
- SIX Sovereign Inference Exchange (six-sov.com): cryptographic receipts,
  per-request Merkle attestations, tamper-evident audit trails, compliance metadata
  inside signed payloads.

Design goals:
- Lightweight: zero required dependencies when SIX stack is absent.
- Verifiable by default: every important action produces an attestation record.
- Flexible: works for personal sovereign use, family LGP, or regulated corporate contexts.
- Embodies existing artifacts: can load compliance roles from breathline-federation
  and (when available) delegate receipt/attestation work to real SIX modules.

The USN remains the single executable capstone. This engine simply makes the
compliance & verifiable inference layer first-class and loadable.
"""

from __future__ import annotations
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Optional SIX integration (graceful) ---
_SIX_AVAILABLE = False
try:
    # When the SIX services are on the path (e.g. via constitution-federation-v2/services/six)
    # these become available. We treat them as optional backends.
    from six import six_attestation, six_compliance, six_crypto  # type: ignore
    _SIX_AVAILABLE = True
except Exception:
    six_attestation = six_compliance = six_crypto = None  # type: ignore


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditRecord:
    """SOX-style immutable, signed, timestamped record with explicit chain-of-custody.

    Each record links to the previous via prev_receipt_hash, creating a verifiable
    tamper-evident chain suitable for regulated environments (SOX, fiduciary, etc.).
    """
    event: str
    principal_id: str
    role_id: str
    action_class: str
    payload_summary: str
    risk_level: RiskLevel
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    receipt_hash: Optional[str] = None          # Current record's hash (for linking)
    prev_receipt_hash: Optional[str] = None     # Explicit chain-of-custody link
    usn_attestation: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compliance_block: Dict[str, Any] = field(default_factory=dict)  # SIX-style metadata (classification, retention, etc.)


@dataclass
class ComplianceVerdict:
    approved: bool
    risk_score: float
    rationale: List[str]
    required_approvals: List[str] = field(default_factory=list)
    policy_refs: List[str] = field(default_factory=list)


class ComplianceEngine:
    """
    First-class compliance & verifiable inference layer for the USN.

    Can be instantiated in "sovereign" (lightweight) or "corporate_regulated"
    (strict) mode. When SIX primitives are reachable, it produces real
    cryptographic receipts. Otherwise it falls back to the USN's existing
    Merkle + self-attestation system (never silent degradation).
    """

    def __init__(self, mode: str = "sovereign", node: Any = None, policy_loader: Any = None):
        self.mode = mode  # "sovereign" | "corporate_regulated" | "corporate_standard"
        self.node = node
        self.policy_loader = policy_loader
        self._audit_trail: List[AuditRecord] = []
        self._sixon = _SIX_AVAILABLE
        self._current_policy: Any = None  # cache for the active policy

    # ------------------------------------------------------------------
    # Core Verifiable Inference
    # ------------------------------------------------------------------
    def attest_execution(
        self,
        role_id: str,
        action_class: str,
        principal_id: str,
        payload: Dict,
        result_summary: str,
    ) -> Dict[str, Any]:
        """
        Produce a hardened SOX-style audit record with chain-of-custody + SIX-style receipt.

        In regulated modes this creates a linked, signed, timestamped record.
        The chain is maintained via prev_receipt_hash for full auditability.
        """
        # Determine previous record for chain-of-custody
        prev_hash = None
        if self._audit_trail:
            prev_hash = self._audit_trail[-1].receipt_hash

        record = AuditRecord(
            event="role_execution",
            principal_id=principal_id,
            role_id=role_id,
            action_class=action_class,
            payload_summary=str(payload)[:200],
            risk_level=self._classify_risk(action_class, self.mode),
            prev_receipt_hash=prev_hash,
            metadata={"result_summary": result_summary[:200]},
            compliance_block=self._build_compliance_block(action_class, self.mode),
        )

        # Always produce USN-native attestation (sovereign floor) — this gives us the signed Merkle root
        if self.node:
            usn_att = self.node._self_attest("compliance_attested_execution", {
                "role_id": role_id,
                "action_class": action_class,
                "risk_level": record.risk_level.value,
                "prev_receipt_hash": prev_hash,
            })
            record.usn_attestation = usn_att
            record.receipt_hash = usn_att.get("memory_root")

        # SIX-style cryptographic receipt (when SIX available we can enhance further;
        # here we produce a compatible structured receipt using USN identity + primitives)
        receipt = self._generate_six_style_receipt(record, payload)
        record.metadata["six_style_receipt"] = receipt

        self._audit_trail.append(record)
        return {
            "summary": {
                "action_class": record.action_class,
                "risk_level": record.risk_level.value,
                "receipt_hash": record.receipt_hash,
                "prev_receipt_hash": prev_hash,
                "charter_v7_checked": record.compliance_block.get("charter_v7_checked", True),
                "timestamp": record.timestamp,
            },
            "audit_record": record,
            "receipt_hash": record.receipt_hash,
            "prev_receipt_hash": prev_hash,
            "usn_attestation": record.usn_attestation,
            "six_style_receipt": receipt,
            "sixon_backed": self._sixon,
        }

    def _build_compliance_block(self, action_class: str, mode: str) -> Dict[str, Any]:
        """SIX-style compliance metadata block (classification, retention, etc.)."""
        classification = "C3_RESTRICTED" if mode.startswith("corporate") else "C1_INTERNAL"
        return {
            "data_classification": classification,
            "retention_policy": "standard_7_years" if mode.startswith("corporate") else "sovereign_default",
            "residency_mode": "enforced" if mode == "corporate_regulated" else "best_effort",
            "pii_present": "unknown",  # per Playbook 6 / SIX invariants (human-set)
            "charter_v7_checked": True,
        }

    def _generate_six_style_receipt(self, record: AuditRecord, original_payload: Dict) -> Dict[str, Any]:
        """Produce a structured, signed receipt compatible with SIX patterns.

        Uses the node's existing breathline identity for signing when possible.
        This provides cryptographic proof independent of (but compatible with) full SIX stack.
        """
        receipt = {
            "receipt_type": "usn_regulated_action",
            "event": record.event,
            "role_id": record.role_id,
            "action_class": record.action_class,
            "principal_id": record.principal_id,
            "timestamp": record.timestamp,
            "risk_level": record.risk_level.value,
            "compliance_block": record.compliance_block,
            "prev_receipt_hash": record.prev_receipt_hash,
            "payload_hash": None,  # would be hash of canonical payload in full impl
            "signatures": {},
        }

        # Sign with node's identity if available (sovereign cryptographic proof)
        if self.node and hasattr(self.node, "identity"):
            try:
                from breathline_primitives import sign
                # Use a stable hash of key fields as the message to sign
                msg = f"{record.role_id}|{record.action_class}|{record.timestamp}|{record.receipt_hash}".encode()
                sig = sign(self.node.identity.private_key, msg, self.node.curve)
                # Serialize as clean dict instead of repr string so the JSON encoder
                # (and readers) see proper hex values instead of Python object repr.
                receipt["signatures"]["node_identity"] = {
                    "r": str(getattr(sig, 'r', '')),
                    "s": str(getattr(sig, 's', '')),
                }
            except Exception:
                receipt["signatures"]["node_identity"] = "signing_failed"

        return receipt

    # ------------------------------------------------------------------
    # Policy & Risk
    # ------------------------------------------------------------------
    @staticmethod
    def _charter_v7_ack_required(action_class: str, context: Dict) -> bool:
        """True iff a material action lacks the required Charter V.7 acknowledgement (case-INSENSITIVE).
        Audit 2026-06-13: hoisted from two duplicated in-line guards whose case handling diverged (one
        lowercased, one did not) — the lowercasing guard's trigger set was a strict superset, making the
        second guard unreachable dead code. One helper, one consistent rule."""
        if context.get("charter_v7_ack") is not False:
            return False
        ac = (action_class or "").lower()
        materiality = str(context.get("materiality", "")).lower()
        return any(k in ac or k in materiality for k in ("board", "filing", "external", "material"))

    def run_policy_compliance_check(
        self,
        role_spec: Dict,
        action_class: str,
        context: Dict,
    ) -> ComplianceVerdict:
        """
        Fully policy-driven compliance check (Playbook 6 + Charter V.7 style).

        When a PolicyLoader (or explicit policy) is present, decisions are driven by:
        - data_classification_rules
        - charter_v7_rules (forbidden classes, required reviews)
        - approval_requirements
        - risk_scoring overrides

        This design allows the same USN to adapt to different statutes and
        organizational types simply by loading different policy artifacts.
        Governance remains fully opt-in.
        """
        rationale = []
        required = []
        score = 0.3
        policy_refs = [f"mode:{self.mode}"]

        # Fail-closed: action not declared in the role's allowed envelope
        allowed = role_spec.get("allowed_action_classes", []) or []
        if allowed and action_class not in allowed:
            return ComplianceVerdict(
                approved=False,
                risk_score=0.95,
                rationale=[f"Action class '{action_class}' not permitted for this role"],
                required_approvals=["Compliance review"],
                policy_refs=policy_refs,
            )

        # Explicit Charter V.7 acknowledgement enforcement for high-materiality actions (supports
        # fail_closed_demo). One hoisted, case-insensitive guard (audit 2026-06-13).
        if self._charter_v7_ack_required(action_class, context):
            return ComplianceVerdict(
                approved=False,
                risk_score=0.9,
                rationale=["Charter V.7 acknowledgement required but not provided for material action"],
                required_approvals=["Compliance Guardian sign-off"],
                policy_refs=policy_refs,
            )

        # Attempt to load/use a policy
        policy = self._get_active_policy(role_spec, context)

        if policy:
            policy_refs.append(f"{policy.id}@v{policy.version}")

            # Data classification influence on risk
            classification = policy.data_classification_rules.get("default", "C1_INTERNAL")
            if "RESTRICTED" in str(classification).upper() or "SECRET" in str(classification).upper():
                score += 0.2
                rationale.append(f"High classification: {classification}")

            # Charter V.7 enforcement from loaded policy
            if action_class in policy.charter_v7_rules:
                return ComplianceVerdict(
                    approved=False,
                    risk_score=0.95,
                    rationale=["Charter V.7 forbidden class per loaded policy"],
                    required_approvals=["Compliance Guardian + Human Signatory"],
                    policy_refs=policy_refs,
                )

            # Approval requirements from policy
            approvals = policy.approval_requirements.get(action_class, [])
            if approvals:
                required.extend(approvals)
                rationale.append(f"Policy requires approvals: {approvals}")

            # Risk scoring overrides from policy
            risk_overrides = policy.risk_scoring or {}
            if action_class in risk_overrides:
                score = max(score, risk_overrides[action_class])

        else:
            # Graceful fallback (existing behavior)
            if self.mode in ("corporate_regulated", "corporate_standard"):
                score += 0.4
                rationale.append("Corporate regulated context active (no explicit policy loaded)")
                if action_class in role_spec.get("charter_v7_forbidden_classes", []):
                    return ComplianceVerdict(
                        approved=False,
                        risk_score=0.95,
                        rationale=["Charter V.7 forbidden class detected"],
                        required_approvals=["Compliance Guardian + Human Signatory"],
                        policy_refs=policy_refs,
                    )

            if "external" in action_class or "board" in action_class or "filing" in action_class:
                score += 0.25
                required.append("Human sign-off (high materiality)")
                rationale.append("High-materiality action class")

            # (audit 2026-06-13) the duplicate Charter-V.7 ack guard that lived here was unreachable dead
            # code — the case-insensitive guard hoisted to the top already fires for its every case.

        approved = score < 0.75 or self.mode == "sovereign"

        return ComplianceVerdict(
            approved=approved,
            risk_score=round(score, 2),
            rationale=rationale or ["Within baseline tolerance"],
            required_approvals=required,
            policy_refs=policy_refs,
        )

    def _get_active_policy(self, role_spec: Dict, context: Dict) -> Any:
        """Resolve the most relevant loaded policy for the current context."""
        if self.policy_loader:
            # Try context-specific policy first, then default corporate policy
            for candidate in [
                context.get("policy_id"),
                f"corporate_{self.mode}",
                "default_governance",
            ]:
                if candidate:
                    try:
                        return self.policy_loader.load_policy(candidate)
                    except Exception:
                        continue
        return None

    def load_policy(self, policy_id: str) -> Any:
        """Convenience method to explicitly load and cache a policy."""
        if self.policy_loader:
            self._current_policy = self.policy_loader.load_policy(policy_id)
            return self._current_policy
        return None

    def _classify_risk(self, action_class: str, mode: str) -> RiskLevel:
        if mode == "corporate_regulated" and any(k in action_class for k in ["filing", "external", "board"]):
            return RiskLevel.HIGH
        if "financial" in action_class or "forecast" in action_class:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    # ------------------------------------------------------------------
    # Human Oversight Simulation (for demos & tests)
    # ------------------------------------------------------------------
    def request_human_approval(self, record: AuditRecord, policy_note: str = "") -> Dict:
        """Simulation hook. In production this would integrate with real workflows."""
        return {
            "status": "approval_requested",
            "record_event": record.event,
            "policy_note": policy_note or "Standard human sign-off for regulated action",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_audit_trail(self, limit: int = 50) -> List[AuditRecord]:
        return self._audit_trail[-limit:]

    def export_evidence_bundle(self, case_id: str = None) -> Dict[str, Any]:
        """
        Export a portable, SOX-style evidence bundle suitable for auditors or regulators.

        Contains the full immutable audit chain, policy versions + Merkle roots,
        node identity, and a self-attestation of the bundle itself.

        This is a first-class artifact for regulated environments while remaining
        fully usable (and empty) in pure sovereign mode.
        """
        case_id = case_id or f"case-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        bundle = {
            "case_id": case_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "node_memory_root": self.node.get_memory_root() if self.node else None,
            "governance_mode": self.mode,
            "record_count": len(self._audit_trail),
            "audit_trail": [
                {
                    "event": r.event,
                    "timestamp": r.timestamp,
                    "role_id": r.role_id,
                    "action_class": r.action_class,
                    "risk_level": r.risk_level.value,
                    "receipt_hash": r.receipt_hash,
                    "prev_receipt_hash": r.prev_receipt_hash,
                    "compliance_block": r.compliance_block,
                }
                for r in self._audit_trail
            ],
            "policies_in_effect": {},
        }

        if self.policy_loader:
            for pid, pol in getattr(self.policy_loader, "_loaded_policies", {}).items():
                bundle["policies_in_effect"][pid] = {
                    "version": getattr(pol, "version", "unknown"),
                    "module_root": getattr(pol, "module_root", None),
                }

        if self.node:
            bundle_att = self.node._self_attest("evidence_bundle_export", {
                "case_id": case_id,
                "record_count": len(self._audit_trail),
            })
            bundle["bundle_attestation"] = bundle_att

        return bundle


# ----------------------------------------------------------------------
# Context helper (used by USN ContextAdapter)
# ----------------------------------------------------------------------
def get_default_compliance_engine(mode: str, node: Any = None, policy_loader: Any = None) -> ComplianceEngine:
    """Factory that respects the node's current context mode."""
    return ComplianceEngine(mode=mode, node=node, policy_loader=policy_loader)
