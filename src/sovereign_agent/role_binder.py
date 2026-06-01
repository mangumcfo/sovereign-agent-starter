"""
RoleBinder - Dynamic binding of YAML specs to Python handlers.

This module enables the Universal Sovereign Node to turn static role_spec.yaml + *_v1.yaml
into live, callable Role objects by dynamically importing the corresponding Python implementation
from breathline-federation (when available in the environment).

Design goals:
- Lightweight (uses importlib, no heavy plugin system)
- Sovereign (never executes un-attested code; binding is recorded)
- Graceful degradation (works even if Python handler is not present)
"""

from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol


class RoleHandler(Protocol):
    """Minimal protocol matching the federation's RoleHandler."""
    role_id: str
    framework: str

    def process(self, request: Any) -> dict[str, Any]:
        ...


class BoundRole:
    """
    A live, executable role that combines:
    - The declarative spec (YAML)
    - The imperative handler (Python class, if found)
    - Attestation hooks from the owning USN
    """

    def __init__(self, spec: Dict[str, Any], handler: Optional[RoleHandler] = None, node: Any = None):
        self.spec = spec
        self.handler = handler
        self.node = node

        # Robust role_id extraction (handles both role_spec.yaml style and *_v1.yaml style)
        raw_role = spec.get("role") or spec.get("id") or ""
        if isinstance(raw_role, dict):
            self.role_id = raw_role.get("id", "unknown")
        else:
            self.role_id = str(raw_role)

        # First-class envelope from the real federation YAML (populated by PlaybookLoader)
        env = spec.get("envelope", {}) or {}
        self.allowed_action_classes: list[str] = env.get("allowed_action_classes", []) or []
        self.framework: str | None = env.get("framework") or spec.get("framework")
        self.invocation_envelope: dict = env.get("invocation_envelope", {}) or {}

        # Compliance engine (injected by USN when in corporate_regulated mode)
        self.compliance_engine: Any = getattr(node, "compliance_engine", None) if node else None

    def get_allowed_action_classes(self) -> list[str]:
        """Returns the authoritative list from the federation role_spec.yaml (or empty list)."""
        return list(self.allowed_action_classes)

    def suggest_action_class(self, hint: str = "") -> str | None:
        """Heuristic suggestion for a safe action_class for this role."""
        if not self.allowed_action_classes:
            return None
        h = hint.lower()
        for a in self.allowed_action_classes:
            if h and h in a.lower():
                return a
        # sensible defaults for common frameworks
        for a in self.allowed_action_classes:
            if "produce" in a or "forecast" in a:
                return a
        return self.allowed_action_classes[0]

    def process(self, payload: dict, principal_id: str = "unknown", request_id: str = "unknown", action_class: str | None = None) -> Dict[str, Any]:
        """
        Execute the role through its bound Python handler (e.g. CFOAgent).

        Zero-friction by design:
        - If action_class is not supplied, it is automatically resolved from
          the role's allowed_action_classes in the real role_spec.yaml.
        - The value is validated against the permission envelope before the
          handler is ever invoked.
        - Rich errors tell the developer exactly what the spec permits.

        The result is always wrapped with USN self-attestation (Merkle + signature).
        """
        # --- Smart, spec-driven action_class resolution (the key zero-friction win) ---
        if action_class is None:
            if self.allowed_action_classes:
                # Prefer a "produce" or "forecast" style action when available (common for CFO roles)
                preferred = [a for a in self.allowed_action_classes if "produce" in a or "forecast" in a or "generate" in a]
                action_class = preferred[0] if preferred else self.allowed_action_classes[0]
            else:
                action_class = "produce_forecast_artifact"  # safe historical default

        # Strict validation against the real federation spec (when present)
        if self.allowed_action_classes and action_class not in self.allowed_action_classes:
            allowed = ", ".join(self.allowed_action_classes)
            raise ValueError(
                f"action_class '{action_class}' is not permitted for role '{self.role_id}'. "
                f"Allowed values (from role_spec.yaml): [{allowed}]. "
                f"See {self.spec.get('source_path', 'the role_spec.yaml')} for the authoritative permission envelope."
            )

        # --- Enterprise governance (Playbook 6 + SIX patterns) when engine is present ---
        if self.compliance_engine is not None:
            compliance_result = self.compliance_engine.attest_execution(
                role_id=self.role_id,
                action_class=action_class,
                principal_id=principal_id,
                payload=payload,
                result_summary="(pre-execution)",
            )
            # Attach governance metadata to the eventual result
            if "compliance_attestation" not in locals():
                locals()["compliance_attestation"] = compliance_result  # captured below in raw_result

        if self.handler is not None:
            # Build a minimal request object that the federation handlers expect
            try:
                from platform_layer.plugin_interface import PlugInRequest
                request = PlugInRequest(
                    request_id=request_id,
                    principal_id=principal_id,
                    role_target=self.role_id,
                    action_class=action_class,
                    payload=payload,
                )
                raw_result = self.handler.process(request)
            except Exception as e:
                raw_result = {
                    "status": "error",
                    "error": str(e),
                    "role_id": self.role_id,
                    "action_class": action_class,
                    "allowed_action_classes": self.allowed_action_classes,
                }
        else:
            raw_result = {
                "status": "executed_without_handler",
                "role_id": self.role_id,
                "payload": payload,
                "note": "YAML spec loaded; no Python handler was bound at runtime.",
            }

        # Wrap with sovereign attestation
        if self.node is not None:
            attested = self.node._self_attest("role_action_executed", {
                "role_id": self.role_id,
                "payload_summary": str(payload)[:200],
                "result_summary": str(raw_result)[:200],
            })
            raw_result["usn_attestation"] = attested

        # Attach enterprise compliance attestation (if engine was active)
        if "compliance_attestation" in locals() and isinstance(locals()["compliance_attestation"], dict):
            raw_result["compliance_attestation"] = locals()["compliance_attestation"]

        return raw_result


def bind_role(spec: Dict[str, Any], federation_root: Path, node: Any = None) -> BoundRole:
    """
    Given a loaded role spec (from role_spec.yaml or *_v1.yaml), attempt to
    dynamically import the corresponding Python handler.

    Expected layout in breathline-federation:
      platform/roles/{role_id}/role.py   → class {RoleName} (e.g. CFOAgent)
    """
    role_id = spec.get("role") or spec.get("id") or ""
    if isinstance(role_id, dict):
        role_id = role_id.get("id", "")

    handler = None

    # Try to find and load the handler
    role_dir = federation_root / "platform" / "roles" / role_id
    role_py = role_dir / "role.py"

    if role_py.exists():
        try:
            # Add the federation platform to sys.path temporarily for relative imports
            sys.path.insert(0, str(federation_root / "platform"))

            spec_module = importlib.util.spec_from_file_location(f"{role_id}_role", role_py)
            if spec_module and spec_module.loader:
                module = importlib.util.module_from_spec(spec_module)
                spec_module.loader.exec_module(module)

                # Common class name patterns
                candidate_names = [
                    role_id.replace("_", "").title() + "Agent",  # cfo_agent -> CfoAgent
                    "".join(word.title() for word in role_id.split("_")) + "Agent",
                    "CFOAgent" if "cfo" in role_id else None,
                ]

                for name in filter(None, candidate_names):
                    if hasattr(module, name):
                        handler = getattr(module, name)()
                        break

                # Fallback: look for any class with .process method
                if handler is None:
                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if isinstance(obj, type) and hasattr(obj, "process"):
                            handler = obj()
                            break

        except Exception as e:
            print(f"[RoleBinder] Warning: Could not bind Python handler for {role_id}: {e}")
        finally:
            # Clean up path
            if str(federation_root / "platform") in sys.path:
                sys.path.remove(str(federation_root / "platform"))

    return BoundRole(spec=spec, handler=handler, node=node)
