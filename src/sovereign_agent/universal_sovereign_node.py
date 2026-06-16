"""
Universal Sovereign Node

The capstone execution kernel for the Agentic AI Playbooks series and the broader Constitutional Federation sovereign architecture.

Lightweight, bootable, context-adaptive, playbook-loading, breathline_primitives-powered sovereign execution environment.

Features:
- Auto-aligns to host context (family, corporate, infrastructure, personal, public)
- Loads playbooks as attested constitutional modules
- Cryptographic root via breathline_primitives (default authorized-v1.0.1)
- Role-based authority
- Verifiable state with generational inheritance
- Secure multi-node collaboration hooks

This evolves the Sovereign Agent Starter into the Universal Sovereign Node.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cryptographic root — lazy surface (audit 2026-06-13 CRIT-2): import never hard-fails on a substrate-
# less host; names resolve on first USE, call sites unchanged.

# Internal modules
from .core import SovereignAgent
from .playbook_loader import PlaybookLoader
from .role_binder import BoundRole


class ContextAdapter:
    """Auto-aligns the node to its host environment.

    Extended to support enterprise-grade governance modes while preserving
    the lightweight sovereign character for family/personal/infrastructure use.
    """

    SUPPORTED_CONTEXTS = [
        "family", "corporate", "corporate_standard", "corporate_regulated",
        "infrastructure", "personal", "public"
    ]

    def __init__(self, context_type: str = "personal"):
        if context_type not in self.SUPPORTED_CONTEXTS:
            context_type = "personal"
        self.context_type = context_type
        self.roles = self._load_default_roles()
        self.governance_mode = self._derive_governance_mode()

    def _load_default_roles(self) -> List[str]:
        if self.context_type == "family":
            return ["family_cfo", "household_synthesis", "legacy_steward", "family_compliance_shield"]
        elif self.context_type.startswith("corporate"):
            return ["cfo_agent", "compliance_agent", "compliance_guardian", "synthesis_agent"]
        elif self.context_type == "infrastructure":
            return ["synthesis_agent", "compliance_guardian", "node_operator"]
        else:
            return ["general_sovereign_agent"]

    def _derive_governance_mode(self) -> str:
        if self.context_type == "corporate_regulated":
            return "corporate_regulated"
        if self.context_type == "corporate_standard":
            return "corporate_standard"
        if self.context_type == "infrastructure":
            return "infrastructure"
        if self.context_type == "family":
            return "sovereign"   # Family is sovereign with generational defaults
        return "sovereign"

    def adapt(self, node_state: Dict) -> Dict:
        node_state["active_context"] = self.context_type
        node_state["active_roles"] = self.roles
        node_state["governance_mode"] = self.governance_mode
        return node_state


class UniversalSovereignNode(SovereignAgent):
    """
    The capstone execution kernel.

    Inherits from SovereignAgent for core identity/memory/governance.
    Adds context adaptation, playbook loading, role-based authority, and multi-node hooks.

    The real PlaybookLoader (from .playbook_loader) + RoleBinder now provides
    the federation binding path: YAML role_spec + *_v1.yaml from breathline-federation
    are dynamically bound to live Python handlers (e.g. CFOAgent / FORECAST) and
    wrapped with Merkle + USN self-attestation on every load and execution.
    """

    def __init__(self, name: str = "UniversalSovereignNode", context_type: str = "personal", 
                 playbooks_root: Optional[Path] = None, memory_path: Optional[Path] = None,
                 auto_bootstrap: bool = True):
        """
        auto_bootstrap=True (default) attempts pure-Python activation of breathline_primitives
        on instantiation. Set False if you have already activated via shell or manual call.
        """
        if auto_bootstrap:
            try:
                from .bootstrap import ensure_breathline_primitives
                ensure_breathline_primitives()
            except Exception as e:
                # User may have activated via shell or pip install -e; the lazy crypto surface
                # (_lazy_bp) keeps the node usable regardless. Log at debug so the swallow is
                # observable when diagnosing (audit 2026-06-13d #26) without noising normal runs.
                logger.debug("auto_bootstrap of breathline_primitives skipped: %s", e)

        super().__init__(name, memory_path)
        
        self.context_adapter = ContextAdapter(context_type)

        # Federation-first loader (real implementation in playbook_loader.py + RoleBinder).
        # playbooks_root kept for backward compatibility with older call sites / examples.
        # Real loader defaults to breathline-federation/platform/roles + specs/ when not overridden.
        # Use centralized resolver (supports env vars, demo mode, and legacy locations)
        from . import config as sovereign_config
        primary_source = playbooks_root or sovereign_config.resolve_primary_source()
        self.playbook_loader = PlaybookLoader(primary_source=primary_source)
        self.loaded_playbooks: Dict[str, Dict] = {}
        self.roles: List[str] = self.context_adapter.roles
        self.loaded_roles: Dict[str, "BoundRole"] = {}   # Multi-role support

        # Enterprise-grade governance layer (Playbook 6 + SIX patterns embodied)
        # Only activates meaningfully in corporate_* contexts; fully graceful otherwise.
        from .compliance.compliance_engine import get_default_compliance_engine
        from .compliance.policy_loader import PolicyLoader

        policy_loader = None
        if self.context_adapter.governance_mode.startswith("corporate"):
            try:
                policy_loader = PolicyLoader()
            except Exception:
                pass  # graceful

        self.compliance_engine = get_default_compliance_engine(
            self.context_adapter.governance_mode, self, policy_loader=policy_loader
        )

        self._self_attest("node_initialized", {
            "context": context_type,
            "roles": self.roles,
            "governance_mode": self.context_adapter.governance_mode
        })

    def adapt_to_context(self, context_type: str):
        """Dynamically re-align to a new host context."""
        self.context_adapter = ContextAdapter(context_type)
        self.roles = self.context_adapter.roles
        self._self_attest("context_adapted", {"new_context": context_type})

    def load_playbook(self, playbook_id: str) -> Dict:
        """Load a playbook (or role) as an attested constitutional module via the real federation loader."""
        module = self.playbook_loader.load_playbook(playbook_id, self)
        self.loaded_playbooks[playbook_id] = module
        self._self_attest("playbook_loaded", {"playbook_id": playbook_id})
        return module

    def load_role(self, role_name: str) -> "BoundRole":
        """
        Load a role from breathline-federation (role_spec.yaml + *_v1.yaml) and return
        a BoundRole that can execute the real Python handler (e.g. CFOAgent + FORECAST framework).

        The returned BoundRole.process(...) will:
        - Invoke the live handler from platform/roles/{role}/role.py if present
        - Always wrap the result with USN self-attestation (Merkle + signature via breathline_primitives)
        """
        module = self.playbook_loader.load_role(role_name, self)
        self.loaded_playbooks[role_name] = module
        self._self_attest("role_loaded", {"role": role_name})

        bound_role = module.get("bound_role", module)
        self.loaded_roles[role_name] = bound_role   # Persist for /execute, cross-role review, status, etc.
        return bound_role

    def discover_playbooks(self) -> list[str]:
        """Discover available playbooks/roles from the primary source (breathline-federation)."""
        try:
            return self.playbook_loader.discover_roles()
        except Exception as e:
            logger.warning("playbook discovery failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Multi-Role Orchestration (Enterprise Governance)
    # ------------------------------------------------------------------
    def load_roles(self, role_names: List[str]) -> Dict[str, "BoundRole"]:
        """
        Load multiple roles simultaneously for coordinated execution.

        Returns a dict of role_name -> BoundRole.
        Each role is also available via self.loaded_roles.
        """
        results = {}
        for name in role_names:
            try:
                br = self.load_role(name)  # reuses single-role path + attestation
                results[name] = br
                self.loaded_roles[name] = br
            except Exception as e:
                logger.warning("[MultiRole] failed to load role '%s': %s", name, e)
        self._self_attest("multi_roles_loaded", {"roles": list(results.keys())})
        return results

    def request_cross_role_review(
        self,
        reviewer_role: str,
        target_role: str,
        artifact: Dict[str, Any],
        principal_id: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Cross-role handoff with authority gradient.

        Example: CFO produces forecast → Compliance reviews it.
        Produces a joint attestation capturing the review + outcome.
        """
        if reviewer_role not in self.loaded_roles:
            self.load_role(reviewer_role)
        if target_role not in self.loaded_roles:
            self.load_role(target_role)

        reviewer = self.loaded_roles.get(reviewer_role)
        if not reviewer or not reviewer.handler:
            return {"status": "error", "reason": f"Reviewer role '{reviewer_role}' not executable"}

        # The reviewer role (e.g. compliance_agent) executes the review
        review_result = reviewer.process(
            payload={"peer_artifact": artifact, "target_role": target_role},
            principal_id=principal_id,
            request_id=f"cross-review-{target_role}-{reviewer_role}",
        )

        # Joint attestation on the handoff
        joint_att = self._self_attest("cross_role_handoff", {
            "reviewer": reviewer_role,
            "target": target_role,
            "review_status": review_result.get("status"),
        })

        review_result["cross_role_attestation"] = joint_att
        review_result["authority_gradient"] = f"{reviewer_role} reviews {target_role} (veto possible per Charter V.7)"

        return review_result

    def execute_role_action(self, role: str, action: str, context: Dict = None) -> Dict:
        """Role-based authority enforcement (now with optional kernel primitive gates)."""
        if role not in self.roles:
            raise PermissionError(f"Role {role} not authorized in current context {self.context_adapter.context_type}")
        
        # Delegate to constitutional governor (kernel primitives engaged when present)
        check = self.constitutional_check(f"{role}:{action}", context or {})
        if not check["approved"]:
            raise PermissionError("Action blocked by Constitutional Governor")

        result = super().act(f"[{role}] {action}", context)
        result["executing_role"] = role

        # Record via kernel auditor if available (deep audit chaining)
        if hasattr(self, "governor") and getattr(self.governor, "kernel_critic", None):
            from . import kernel_integration as _ki
            _ki.record_kernel_usage(self, "Auditor", {"role": role, "action": action})

        return result

    def collaborate_with_node(self, other_node: "UniversalSovereignNode", message: str, payload: Dict = None) -> Dict:
        """
        Secure multi-node collaboration with rich attested handoff.

        Supports:
        - Simple messages
        - Structured payloads (e.g., legacy notes, role summaries, memory roots)
        - Full USN self-attestation of the collaboration event

        This is the foundation for real mesh/federation collaboration while
        remaining pure Python and local-first in the base case.
        """
        payload = payload or {}
        collab_data = {
            "with_node": other_node.name,
            "message": message,
            "payload_summary": str(payload)[:300] if payload else None,
            "sender_memory_root": self.get_memory_root(),
        }

        collab_attestation = self._self_attest("node_collaboration", collab_data)

        return {
            "status": "attested_handoff_sent",
            "from": self.name,
            "to": other_node.name,
            "message": message,
            "payload": payload,
            "sender_memory_root": self.get_memory_root(),
            "attestation": collab_attestation,
            "verifiable": True,
        }

    def get_status(self) -> Dict[str, Any]:
        """Full verifiable status report."""
        return {
            "name": self.name,
            "context": self.context_adapter.context_type,
            "active_roles": self.roles,
            "loaded_playbooks": list(self.loaded_playbooks.keys()),
            "memory_root": self.get_memory_root(),
            "identity_public": str(self.identity.public_key)[:64] + "...",
            "merkle_mode": os.environ.get("BREATHLINE_MERKLE_MODE", "authorized-v1.0.1")
        }

    # ------------------------------------------------------------------
    # Light Multi-Node Federation Support (Phase 5 foundation)
    # ------------------------------------------------------------------

    _node_registry: Dict[str, "UniversalSovereignNode"] = {}  # Simple in-memory registry for local simulations

    @classmethod
    def register_node(cls, node: "UniversalSovereignNode") -> None:
        """Register a node for local multi-node discovery (simulation / development)."""
        cls._node_registry[node.name] = node

    @classmethod
    def discover_node(cls, name: str) -> Optional["UniversalSovereignNode"]:
        """Discover another node by name (light federation simulation)."""
        return cls._node_registry.get(name)

    @classmethod
    def list_known_nodes(cls) -> List[str]:
        """List all locally known nodes (for demo / federation UI)."""
        return list(cls._node_registry.keys())


# Convenience factory
def create_universal_sovereign_node(name: str = "USN", context: str = "personal") -> UniversalSovereignNode:
    return UniversalSovereignNode(name=name, context_type=context)


def cli_create_node() -> None:
    """
    Entry point for the `sovereign-node` console script.

    This function exists so that `pip install -e ".[portal]"` produces
    a working `sovereign-node` command. It is intentionally a thin,
    user-friendly wrapper around the existing class + context detection.
    """
    # We import here to avoid circular issues at module load time
    from .bootstrap import _auto_detect_context
    from .config import is_demo_mode

    print("\n∞Δ∞ Sovereign Node (sovereign-node)")

    ctx = _auto_detect_context()
    node = UniversalSovereignNode(context_type=ctx)

    print(f"Context: {ctx}  |  Mode: {'DEMO' if is_demo_mode() else 'FULL'}")
    print(f"Memory root: {node.get_memory_root()[:32]}...")
    print(f"Active roles: {node.roles}")

    if is_demo_mode():
        print("\n[DEMO] Bundled roles available. Load one with node.load_role('family_cfo_agent') etc.")

    print("\nNode is live and ready for sovereign work.")
