"""
PolicyLoader — Rich, dynamic loader for Playbook 6-style governance policies.

Mirrors the design of PlaybookLoader for consistency:
- Primary source: breathline-federation (platform/governance_policies/ or specs/governance/)
- Secondary: KDP vault for published policy documents
- Returns structured Policy objects with sections for:
    - data_classification_rules
    - charter_v7_rules
    - retention_rules
    - approval_requirements
    - risk_scoring
- Supports basic versioning (via YAML 'version' field) and hot-reload (file mtime check).

Policies are first-class loadable artifacts, enabling the USN to be flexible across
different statutes and organizational types while staying constitutionally anchored.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import yaml

from breathline_primitives import MerkleTree, hash_function


@dataclass
class Policy:
    """Structured representation of a loaded governance policy."""
    id: str
    version: str
    source_path: str
    data_classification_rules: Dict[str, Any] = field(default_factory=dict)
    charter_v7_rules: List[str] = field(default_factory=list)
    retention_rules: Dict[str, Any] = field(default_factory=dict)
    approval_requirements: Dict[str, Any] = field(default_factory=dict)
    risk_scoring: Dict[str, Any] = field(default_factory=dict)
    raw_content: Dict[str, Any] = field(default_factory=dict)
    module_root: Optional[str] = None   # Merkle root for attestation


class PolicyLoader:
    """
    Loads Playbook 6-style policy definitions dynamically.

    Usage (consistent with PlaybookLoader):
        loader = PolicyLoader()
        policy = loader.load_policy("corporate_finance_governance_v1")
        engine = ComplianceEngine(..., policy_loader=loader)
    """

    def __init__(self, primary_source: Optional[Path] = None, secondary_source: Optional[Path] = None):
        from .. import config as sovereign_config
        self.primary_source = primary_source or sovereign_config.resolve_primary_source()
        # Books vault via config (BREATHLINE_BOOKS_VAULT; legacy path is a candidate) — runs anywhere.
        self.secondary_source = secondary_source or sovereign_config.get_playbooks_dir()
        self._loaded_policies: Dict[str, Policy] = {}
        self._file_mtimes: Dict[str, float] = {}  # for hot-reload detection

    def discover_policies(self) -> List[str]:
        """Discover available policy keys from breathline-federation."""
        policies = set()

        # Convention 1: platform/governance_policies/
        gov_dir = self.primary_source / "platform" / "governance_policies"
        if gov_dir.exists():
            for pfile in gov_dir.glob("*.policy.yaml"):
                policies.add(pfile.stem.replace(".policy", ""))

        # Convention 2: specs/governance/ (or any *_policy_v*.yaml)
        specs_dir = self.primary_source / "specs"
        if specs_dir.exists():
            for category in specs_dir.iterdir():
                if category.is_dir():
                    for pfile in category.glob("*policy*.yaml"):
                        key = pfile.stem.replace("_v1", "").replace("_v2", "")
                        policies.add(key)

        return sorted(list(policies))

    def load_policy(self, policy_id: str, force_reload: bool = False) -> Policy:
        """
        Load a policy definition.

        Supports hot-reload if the underlying file has changed since last load.
        """
        cache_key = policy_id

        # Check for hot-reload
        if not force_reload and cache_key in self._loaded_policies:
            # Simple mtime check (can be made more sophisticated)
            source_path = self._find_policy_path(policy_id)
            if source_path and self._has_file_changed(source_path):
                force_reload = True

        if cache_key in self._loaded_policies and not force_reload:
            return self._loaded_policies[cache_key]

        content = None
        source_path = None

        # Try primary federation locations
        candidates = [
            self.primary_source / "platform" / "governance_policies" / f"{policy_id}.policy.yaml",
            self.primary_source / "specs" / "governance" / f"{policy_id}.yaml",
        ]

        for cand in candidates:
            if cand.exists():
                source_path = cand
                with open(cand, "r") as f:
                    content = yaml.safe_load(f)
                break

        if content is None:
            # Fallback placeholder for development / missing policies
            content = {
                "id": policy_id,
                "version": "0.0",
                "data_classification_rules": {"default": "C1_INTERNAL"},
                "charter_v7_rules": [],
                "retention_rules": {"default": "sovereign_default"},
                "approval_requirements": {},
                "risk_scoring": {"base": 0.3},
            }
            source_path = "placeholder"

        # Build structured Policy
        policy = Policy(
            id=content.get("id", policy_id),
            version=content.get("version", "1.0"),
            source_path=str(source_path),
            data_classification_rules=content.get("data_classification_rules", {}),
            charter_v7_rules=content.get("charter_v7_rules", content.get("charter_v7_forbidden_classes", [])),
            retention_rules=content.get("retention_rules", {}),
            approval_requirements=content.get("approval_requirements", {}),
            risk_scoring=content.get("risk_scoring", {}),
            raw_content=content,
        )

        # Compute Merkle root over the policy content for attestation
        canonical = json.dumps(content, sort_keys=True).encode()
        leaf = hash_function(canonical)
        tree = MerkleTree([leaf])
        policy.module_root = tree.get_root().hex()

        self._loaded_policies[cache_key] = policy
        if isinstance(source_path, Path):
            self._file_mtimes[str(source_path)] = source_path.stat().st_mtime

        return policy

    def _find_policy_path(self, policy_id: str) -> Optional[Path]:
        candidates = [
            self.primary_source / "platform" / "governance_policies" / f"{policy_id}.policy.yaml",
            self.primary_source / "specs" / "governance" / f"{policy_id}.yaml",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _has_file_changed(self, path: Path) -> bool:
        current_mtime = path.stat().st_mtime if path.exists() else 0
        last = self._file_mtimes.get(str(path), 0)
        return current_mtime > last

    def reload_policy(self, policy_id: str) -> Policy:
        """Explicit hot-reload."""
        return self.load_policy(policy_id, force_reload=True)

    def get_active_policy(self) -> Optional[Policy]:
        """Return the last successfully loaded policy (with its Merkle root for attestation)."""
        return self._current_policy

    def list_loaded_policies(self) -> Dict[str, str]:
        """Return {policy_id: version} for all currently loaded policies."""
        return {pid: p.version for pid, p in self._loaded_policies.items()}
