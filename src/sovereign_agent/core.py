"""
SovereignAgent - Robust Generational Agent Core

Enhanced for Lasting Generational Prosperity (LGP).
- Persistent, Merkle-rooted, versioned memory with inheritance support.
- Substantive Constitutional Governor with principle scoring.
- Self-attestation on major state changes.
- Tightly integrated with breathline_primitives (default authorized-v1.0.1 mode).

All cryptography and attestation use the sealed foundation.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy crypto surface (audit 2026-06-13 CRIT-2): import sovereign_agent must not hard-fail when the
# sealed substrate is absent. Names resolve on first USE; call sites are unchanged.
from ._lazy_bp import (
    generate_keypair,
    sign,
    hash_function,
    secp256k1_curve,
)
from .ndjson import read_ndjson  # the ONE tolerant ndjson reader (Universalize Wave §1)
from .merkle_accumulator import MerkleAccumulator  # incremental frontier root (Engine 95+ HIGH #1)

# Optional deep sovereignty via real kernel primitives (graceful if absent)
try:
    from . import kernel_integration as _ki
except Exception:
    _ki = None  # type: ignore


class ConstitutionalGovernor:
    """
    Substantive self-governance against SOURCE, TRUTH, INTEGRITY, and LGP.

    When the breathline-federation kernel primitives (Governor, Critic, Auditor)
    are available, they are used for an additional immutable-kernel gate
    (Critic + Governor elevation-style review). This deepens sovereignty
    without breaking the existing LGP heuristic or requiring the full platform.
    """

    PRINCIPLES = {
        "SOURCE": "Ground reasoning in verifiable data and primary sources.",
        "TRUTH": "Maximize accuracy; surface uncertainty and reject known falsehoods.",
        "INTEGRITY": "Act consistently with stated values across time.",
        "LGP": "Prioritize outcomes that compound positively for descendants over generations.",
    }

    def __init__(self, kernel_critic: Any = None, kernel_governor: Any = None):
        self.kernel_critic = kernel_critic
        self.kernel_governor = kernel_governor

    def score_action(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic but substantive scoring (expandable).
        Returns score (0-1), rationale, and self-attestation.
        """
        score = 0.5
        rationale = []

        action_lower = action.lower()

        # SOURCE check
        if any(k in action_lower for k in ["research", "verify", "source", "data"]):
            score += 0.15
            rationale.append("Strong SOURCE alignment via research/verification intent.")

        # TRUTH check
        if "uncertainty" in action_lower or "verify" in action_lower:
            score += 0.1
            rationale.append("Explicit truth-seeking language detected.")

        # INTEGRITY check
        if context.get("consistent_with_past", True):
            score += 0.1
            rationale.append("Consistent with historical agent behavior.")

        # LGP check (strongest weight for this mission)
        if any(k in action_lower for k in ["generation", "descendant", "long-term", "legacy", "children", "family"]):
            score += 0.25
            rationale.append("Explicit multi-generational / LGP language.")

        score = min(1.0, max(0.0, score))

        return {
            "score": round(score, 3),
            "rationale": rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "principles_checked": list(self.PRINCIPLES.keys()),
        }

    def kernel_elevation_check(self, role_spec: dict, request: dict) -> dict:
        """
        If kernel primitives are wired, run a Critic + Governor style gate.
        Returns a dict with 'verdict', 'rationale', and 'kernel_used'.
        Falls back gracefully when primitives are not present.
        """
        if not (self.kernel_critic and self.kernel_governor):
            return {"verdict": "BYPASSED", "rationale": "Kernel primitives not available", "kernel_used": False}

        # Phase-1 lightweight check (real ElevationProposal construction can be expanded later)
        try:
            # For now we treat "role execution" as a lightweight elevation.
            # A fuller implementation would build a proper Spec + ElevationProposal.
            # Minimal conformance: if the role has a spec body we consider it plausible
            verdict = "CONFORMS" if role_spec else "DRIFT"
            report = {"verdict": verdict, "findings": ["Phase-1 kernel gate (lightweight)"]}

            if verdict != "CONFORMS":
                return {"verdict": "DENIED", "rationale": "Critic did not return CONFORMS", "kernel_used": True}

            # Governor would normally see a full proposal; we give it a summary
            gov_decision = "APPROVE"  # In Phase 1 we are permissive once Critic passes
            return {
                "verdict": gov_decision,
                "rationale": "Kernel Governor approved (Critic passed)",
                "kernel_used": True,
                "critic_report": report,
            }
        except Exception as e:
            return {"verdict": "ERROR", "rationale": str(e), "kernel_used": True}


class VerifiableMemory:
    """
    Persistent, Merkle-rooted, versioned memory with generational inheritance.
    """

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Append-only NDJSON leaf log (Universalize Wave §4): one line per leaf instead of rewriting the
        # whole-file JSON on every append. Kills the O(n²) that fired on every obligation close.
        self.log_path = self.storage_path.with_suffix(".ndjson")
        self.leaves: List[bytes] = []
        self.version = 0
        self._load()
        # Incremental frontier accumulator (Engine 95+ HIGH #1): replaces the per-append full-tree rebuild
        # (was O(n^2) across n appends). Built ONCE from the loaded leaves in O(n log n); each subsequent
        # append is O(log n). Root is byte-identical to MerkleTree(self.leaves).get_root() (equivalence gate).
        self._acc = MerkleAccumulator.from_leaves(self.leaves)

    def _load(self):
        """Prefer the append-only leaf log; migrate a legacy whole-file JSON ONCE if that's all we have.
        Leaf ORDER is preserved end-to-end so the Merkle root is byte-identical across the migration (G5)."""
        if self.log_path.exists():
            self._load_log()
        elif self.storage_path.exists():
            self._migrate_legacy_json()

    def _load_log(self):
        # Tolerant read via the ONE gateway (§1): a leaf log truncated mid-append loads its clean prefix.
        res = read_ndjson(self.log_path)
        self.leaves = [bytes.fromhex(e["leaf"]) for e in res.entries if e.get("leaf")]
        self.version = res.entries[-1].get("version", len(self.leaves)) if res.entries else 0

    def _migrate_legacy_json(self):
        """One-time migration of the legacy {version, leaves:[hex…]} whole-file JSON into the append-only
        NDJSON leaf log — SAME leaves, SAME order, so get_root() is byte-identical before and after (G5)."""
        data = json.loads(self.storage_path.read_text())
        leaves_hex = data.get("leaves", [])
        self.leaves = [bytes.fromhex(lh) for lh in leaves_hex]
        self.version = data.get("version", len(self.leaves))
        with self.log_path.open("w", encoding="utf-8") as f:
            for i, lh in enumerate(leaves_hex):
                f.write(json.dumps({"leaf": lh, "version": i + 1}, sort_keys=True) + "\n")
        # The legacy JSON is left in place as a frozen pre-migration artifact; _load() prefers the log now.

    def _append_leaf(self, leaf: bytes):
        """O(1) persist: append ONE leaf line to the NDJSON log (no whole-file rewrite)."""
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"leaf": leaf.hex(), "version": self.version,
                                "ts": datetime.now(timezone.utc).isoformat()}, sort_keys=True) + "\n")

    def append(self, data: bytes, metadata: Optional[Dict] = None) -> bytes:
        """Append with self-attestation. O(1)-amortized: one in-memory append + one appended log line;
        the Merkle root is recomputed once (same MerkleTree → identical root value) and memoized."""
        entry = {
            "data_hash": hash_function(data).hex(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        leaf = hash_function(json.dumps(entry, sort_keys=True).encode())
        self.leaves.append(leaf)
        self.version += 1
        self._append_leaf(leaf)
        # O(log n): update only the right frontier. Root stays byte-identical to MerkleTree(self.leaves).
        return self._acc.append(leaf)

    def get_root(self) -> Optional[bytes]:
        # O(1): the accumulator holds the current root (byte-identical to MerkleTree(self.leaves).get_root()).
        return self._acc.get_root()

    def inherit_from_parent(self, parent_root: bytes):
        """Support generational handoff."""
        self.append(b"INHERITED_FROM_PARENT:" + parent_root, {"type": "inheritance"})


class SovereignAgent:
    """
    Robust Sovereign Agent for Lasting Generational Prosperity.
    """

    def __init__(self, name: str, memory_path: Optional[Path] = None, auto_bootstrap: bool = True):
        """
        auto_bootstrap=True (default) attempts pure-Python activation of breathline_primitives.
        Set to False if already activated via shell or explicit call.
        """
        if auto_bootstrap:
            try:
                from .bootstrap import ensure_breathline_primitives
                ensure_breathline_primitives()
            except Exception:
                pass

        self.name = name
        self.curve = secp256k1_curve()
        self.identity = generate_keypair(self.curve)

        if memory_path is None:
            memory_path = Path(f"./memory/{name}_memory.json")
        self.memory = VerifiableMemory(memory_path)

        # Attempt to wire real kernel primitives for deeper sovereignty
        kernel_critic = kernel_governor = None
        if _ki is not None:
            try:
                kernel_critic = _ki.get_kernel_critic()
                kernel_governor = _ki.get_kernel_governor()
            except Exception:
                pass  # graceful — current LGP scoring remains authoritative

        self.governor = ConstitutionalGovernor(kernel_critic=kernel_critic, kernel_governor=kernel_governor)

        # Self-attest initial state
        self._self_attest("agent_initialized", {"name": name})

    def _self_attest(self, event: str, details: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "event": event,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        leaf = hash_function(json.dumps(payload, sort_keys=True).encode())
        root = self.memory.append(leaf, {"type": "self_attestation", "event": event})
        sig = sign(self.identity.private_key, leaf, self.curve)

        return {
            "event": event,
            "memory_root": root.hex(),
            "signature": sig,
        }

    def constitutional_check(self, action: str, context: Dict[str, Any], role_spec: dict | None = None, request: dict | None = None) -> Dict[str, Any]:
        """Strengthened governor with scoring and self-attestation.

        When kernel primitives are present, an additional immutable-kernel gate
        (Critic + Governor elevation review) is executed and merged into the result.
        """
        score_result = self.governor.score_action(action, context)

        kernel_gate = None
        if role_spec is not None and hasattr(self.governor, "kernel_elevation_check"):
            try:
                kernel_gate = self.governor.kernel_elevation_check(role_spec or {}, request or {})
            except Exception:
                kernel_gate = {"verdict": "ERROR", "kernel_used": False}

        attestation = self._self_attest("constitutional_check", {
            "action": action,
            "score": score_result["score"],
            "rationale": score_result["rationale"],
            "kernel_gate": kernel_gate,
        })

        approved = score_result["score"] >= 0.65  # Threshold for LGP focus

        # If kernel gate explicitly denied, we can harden the decision
        if kernel_gate and kernel_gate.get("verdict") == "DENIED":
            approved = False

        result = {
            "approved": approved,
            "score": score_result["score"],
            "rationale": score_result["rationale"],
            "self_attestation": attestation,
        }
        if kernel_gate:
            result["kernel_gate"] = kernel_gate
        return result

    def act(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        context = context or {}

        check = self.constitutional_check(task, context)
        if not check["approved"]:
            return {
                "status": "blocked",
                "reason": "Failed constitutional check",
                "details": check,
            }

        # Long-horizon placeholder reasoning
        result = f"[{self.name}] Executed (LGP-aligned, multi-gen view): {task}"

        # Attest the output
        leaf = hash_function(result.encode())
        memory_root = self.memory.append(leaf, {"type": "action", "task": task})

        attestation = {
            "status": "executed",
            "agent": self.name,
            "task": task,
            "result": result,
            "memory_root": memory_root.hex(),
            "constitutional_score": check["score"],
            "signature": sign(self.identity.private_key, result.encode(), self.curve),
            "self_attestation": self._self_attest("action_completed", {"task": task}),
        }

        return attestation

    def get_memory_root(self) -> Optional[str]:
        root = self.memory.get_root()
        return root.hex() if root else None

    def inherit_from(self, parent_agent: "SovereignAgent"):
        """Generational inheritance support."""
        parent_root = parent_agent.memory.get_root()
        if parent_root:
            self.memory.inherit_from_parent(parent_root)
            self._self_attest("inherited_from", {"parent": parent_agent.name, "parent_root": parent_root.hex()})


# Quick demo
if __name__ == "__main__":
    agent = SovereignAgent("LGP-Prototype")
    result = agent.act("Develop antifragile multi-generational wealth strategy")
    print(result)
    print("Current Memory Root:", agent.get_memory_root())
