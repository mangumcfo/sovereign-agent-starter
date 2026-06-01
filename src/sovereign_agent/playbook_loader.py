"""
PlaybookLoader - Enhanced for Universal Sovereign Node

Intelligently discovers and loads structured constitutional modules from:
- Primary: breathline-federation (platform/roles/, specs/, platform/seed/, kernel primitives)
- Secondary (fallback): KDP/agentic_playbooks vault for narrative/published content

Each loaded item is treated as an attested constitutional module:
- Parsed YAML content
- Computed Merkle root over the canonical representation
- Optional node signature for provenance

This makes the USN the true executable capstone for the Agentic AI Playbooks series.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml  # We may need to add pyyaml; for now assume available or use safe load

from breathline_primitives import MerkleTree, hash_function
from .role_binder import bind_role, BoundRole
from . import config as sovereign_config


class PlaybookLoader:
    """
    Flexible loader for Agentic AI Playbooks and role specs as constitutional modules.
    """

    def __init__(self, primary_source: Optional[Path] = None, secondary_source: Optional[Path] = None):
        # Use centralized resolver (supports demo mode + env vars + legacy paths)
        resolved_primary = sovereign_config.resolve_primary_source(primary_source)
        self.primary_source = resolved_primary
        # Secondary (books vault) kept as legacy fallback only — primary is now fully resolver-driven
        self.secondary_source = secondary_source or Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks")

        self._is_demo = sovereign_config.is_demo_mode() or (resolved_primary == sovereign_config.get_demo_roles_dir())
        self._validate_sources()

    def _validate_sources(self):
        # Not strict — we can work with whatever is present
        pass

    def discover_roles(self) -> List[str]:
        """Discover available role keys from breathline-federation primarily (or demo roles)."""
        roles = set()

        if self._is_demo or self.primary_source == sovereign_config.get_demo_roles_dir():
            # Demo mode: scan the bundled flat demo role directories and return friendly names
            demo_dir = sovereign_config.get_demo_roles_dir()
            for role_dir in demo_dir.iterdir():
                if role_dir.is_dir() and (role_dir / "role_spec.yaml").exists():
                    # Return the friendly alias the rest of the system already uses
                    friendly = next((k for k, v in sovereign_config.DEMO_ROLE_ALIASES.items() if v == role_dir.name), role_dir.name)
                    roles.add(friendly)
            # Always include the base set the portal/examples expect
            for f in sovereign_config.get_friendly_demo_role_names():
                roles.add(f)
            return sorted(list(roles))

        # Full federation path (unchanged behavior)
        # From platform/roles
        roles_dir = self.primary_source / "platform" / "roles"
        if roles_dir.exists():
            for role_dir in roles_dir.iterdir():
                if role_dir.is_dir() and (role_dir / "role_spec.yaml").exists():
                    roles.add(role_dir.name)

        # From specs/ (more versioned specs)
        specs_dir = self.primary_source / "specs"
        if specs_dir.exists():
            for category in specs_dir.iterdir():
                if category.is_dir():
                    for spec_file in category.glob("*_agent_v1.yaml"):
                        role_key = spec_file.stem.replace("_v1", "")
                        roles.add(role_key)
                    for spec_file in category.glob("*_v1.yaml"):
                        if "agent" not in spec_file.name and "constitution" not in spec_file.name:
                            roles.add(spec_file.stem.replace("_v1", ""))

        return sorted(list(roles))

    def load_role(self, role_key: str, node: Optional[Any] = None) -> Dict[str, Any]:
        """
        Load a role (e.g. 'cfo_agent' or 'family_cfo_agent') as an attested constitutional module.

        In demo mode (or when no federation root is configured) this transparently
        serves the bundled self-contained demo roles so the <2-minute onboarding
        experience always works.
        """
        # Demo mode fast path (the key to radical simplicity)
        if self._is_demo or self.primary_source == sovereign_config.get_demo_roles_dir():
            demo_key = sovereign_config.map_to_demo_role(role_key)
            demo_dir = sovereign_config.get_demo_roles_dir() / demo_key
            spec_path = demo_dir / "role_spec.yaml"
            if spec_path.exists():
                with open(spec_path, "r") as f:
                    content = yaml.safe_load(f)
                module = {
                    "id": role_key,
                    "type": "role_spec",
                    "source": "demo-bundled",
                    "loaded_at": None,
                    "content": content,
                    "source_path": str(spec_path),
                    "envelope": {
                        "allowed_action_classes": content.get("allowed_action_classes", []),
                        "invocation_envelope": content.get("invocation_envelope", {}),
                        "framework": content.get("framework") or (content.get("role") or {}).get("framework"),
                    },
                }
                # Compute Merkle (same as normal path)
                canonical = json.dumps(module.get("content", {}), sort_keys=True).encode()
                leaf = hash_function(canonical)
                tree = MerkleTree([leaf])
                module["module_root"] = tree.get_root().hex()
                module["module_hash"] = leaf.hex()

                # Bind using the flat demo layout (role.py lives next to role_spec.yaml)
                bound_role = _bind_demo_role(demo_dir, content, node)
                module["bound_role"] = bound_role
                module["handler_bound"] = bound_role.handler is not None
                return module

        # --- Normal full-federation path (unchanged for power users) ---
        module = {
            "id": role_key,
            "type": "role_spec",
            "source": "breathline-federation",
            "loaded_at": None,
        }

        content = None
        source_path = None

        # Try platform/roles first (role_spec.yaml)
        role_dir = self.primary_source / "platform" / "roles" / role_key
        spec_path = role_dir / "role_spec.yaml"
        if spec_path.exists():
            source_path = spec_path
            with open(spec_path, "r") as f:
                content = yaml.safe_load(f)

        # Try specs/ for more detailed v1 specs
        if content is None:
            for category in (self.primary_source / "specs").iterdir():
                if not category.is_dir():
                    continue
                candidate = category / f"{role_key}_v1.yaml"
                if candidate.exists():
                    source_path = candidate
                    with open(candidate, "r") as f:
                        content = yaml.safe_load(f)
                    break

        if content is None:
            module["content"] = {"note": f"No structured YAML found for {role_key} yet. Using placeholder."}
            module["source"] = "placeholder"
        else:
            module["content"] = content
            module["source_path"] = str(source_path)

            # Extract a clean, first-class envelope for zero-friction execution
            # (allowed_action_classes is the source of truth for BoundRole.process)
            module["envelope"] = {
                "allowed_action_classes": content.get("allowed_action_classes", []),
                "invocation_envelope": content.get("invocation_envelope", {}),
                "framework": content.get("framework") or content.get("role", {}).get("framework") if isinstance(content.get("role"), dict) else content.get("framework"),
            }

        # Compute Merkle root
        canonical = json.dumps(module.get("content", {}), sort_keys=True).encode()
        leaf = hash_function(canonical)
        tree = MerkleTree([leaf])
        module_root = tree.get_root()

        module["module_root"] = module_root.hex()
        module["module_hash"] = leaf.hex()

        # Dynamic binding to Python handler (from breathline-federation when available)
        federation_root = self.primary_source
        bound_role = bind_role(content or {}, federation_root, node)
        module["bound_role"] = bound_role
        module["handler_bound"] = bound_role.handler is not None

        if node is not None:
            attestation = node._self_attest("constitutional_module_loaded", {
                "module_id": role_key,
                "module_root": module["module_root"],
                "source": module.get("source"),
                "handler_bound": module["handler_bound"]
            })
            module["load_attestation"] = attestation

        return module

    def load_constitution(self, constitution_key: str, node: Optional[Any] = None) -> Dict[str, Any]:
        """Load a constitution file (e.g. 'base_constitution_v1' or family one)."""
        # Similar logic, simplified for brevity in this implementation
        return self.load_role(constitution_key, node)  # Reuse for now; can specialize later

    # Keep backward compatibility method
    def load_playbook(self, playbook_id: str, node: Optional[Any] = None) -> Dict[str, Any]:
        """Legacy method for KDP vault. Delegates to role loading where possible."""
        # For now, map playbook names to roles if possible, else placeholder
        role_map = {
            "01_cfos_finance": "cfo_agent",
            "02_executives_decisions": "synthesis_agent",
        }
        role_key = role_map.get(playbook_id, playbook_id)
        return self.load_role(role_key, node)


# ------------------------------------------------------------------
# Demo role binding helper (flat layout: role_spec.yaml + role.py in same dir)
# ------------------------------------------------------------------
def _bind_demo_role(demo_role_dir: Path, spec_content: Dict[str, Any], node: Optional[Any] = None) -> BoundRole:
    """
    Lightweight binder for the bundled demo roles (flat directory layout).
    Avoids touching the real federation platform/roles logic.
    """
    role_py = demo_role_dir / "role.py"
    handler = None
    if role_py.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"demo_{demo_role_dir.name}", role_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # Try common class names
                for candidate in [
                    demo_role_dir.name.replace("_demo", "").replace("_", "").title() + "Agent",
                    "".join(w.title() for w in demo_role_dir.name.split("_")) + "Agent",
                    "FamilyCfoDemoAgent", "CorporateCfoDemoAgent", "GeneralSovereignDemoAgent",
                ]:
                    if hasattr(mod, candidate):
                        handler = getattr(mod, candidate)()
                        break
                if handler is None:
                    # fallback: first class with .process
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if isinstance(obj, type) and hasattr(obj, "process"):
                            handler = obj()
                            break
        except Exception as e:
            print(f"[PlaybookLoader] Demo role bind warning for {demo_role_dir.name}: {e}")

    # Build a minimal envelope the same way the normal path does
    env = {
        "allowed_action_classes": spec_content.get("allowed_action_classes", []),
        "invocation_envelope": spec_content.get("invocation_envelope", {}),
        "framework": spec_content.get("framework"),
    }
    # Inject envelope so BoundRole can read it
    spec_for_bound = dict(spec_content)
    spec_for_bound["envelope"] = env

    return BoundRole(spec=spec_for_bound, handler=handler, node=node)
