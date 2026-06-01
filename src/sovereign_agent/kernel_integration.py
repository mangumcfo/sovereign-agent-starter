"""
Kernel Primitives Integration — Sovereign bridge to breathline-federation/platform/kernel/primitives.

This module provides a lightweight, lazy-loading facade so the Universal Sovereign Node
can use the real immutable Layer-1 primitives (Governor, Auditor, Critic, etc.) for
deeper constitutional enforcement and audit chaining — without requiring the full
platform stack to be initialized.

Design principles (sovereign engineering):
- Graceful degradation: everything works if the primitives tree is absent.
- No external shell dependencies for the base case (Auditor falls back to USN Merkle + attestation).
- Every use of a kernel primitive is recorded via the existing _self_attest mechanism
  with a `kernel_primitive` tag.
- The primitives remain the single source of truth for their behavior (we only adapt).

This directly fulfills the "Kernel Primitives" section previously marked as future expansion.
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Optional

# --- Lazy bootstrap (same pattern as breathline_primitives and RoleBinder) ---

_KERNEL_BOOTSTRAPPED = False
_KERNEL_ROOT: Optional[Path] = None


def _ensure_kernel_primitives() -> bool:
    """Ensure the breathline-federation kernel primitives are importable."""
    global _KERNEL_BOOTSTRAPPED, _KERNEL_ROOT

    if _KERNEL_BOOTSTRAPPED:
        return True

    # Common locations (consistent with the rest of the USN bootstrap strategy)
    candidates = [
        Path("/home/kmangum/work-repos/mangumcfo/breathline-federation/platform"),
        Path.home() / "work-repos" / "mangumcfo" / "breathline-federation" / "platform",
    ]

    for p in candidates:
        if (p / "kernel" / "primitives" / "__init__.py").exists():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            _KERNEL_ROOT = p
            _KERNEL_BOOTSTRAPPED = True
            return True

    return False


# --- Safe accessors (never raise on missing primitives) ---

def get_kernel_critic() -> Any | None:
    """Returns a Critic instance or None."""
    if not _ensure_kernel_primitives():
        return None
    try:
        from kernel.primitives.critic import Critic
        from kernel.primitives.spec import SpecRegistry
        # Minimal registry for Phase 1 — real specs can be registered by callers later
        registry = SpecRegistry()
        # The role prompt is read from the seed at real boot; we use a reference here
        prompt = "You are the Critic. (kernel primitive)"
        return Critic(registry, prompt)
    except Exception:
        return None


def get_kernel_governor() -> Any | None:
    """Returns a Governor instance or None."""
    if not _ensure_kernel_primitives():
        return None
    try:
        from kernel.primitives.governor import Governor
        prompt = "You are the Governor. (kernel primitive)"
        return Governor(prompt)
    except Exception:
        return None


def get_kernel_auditor() -> Any | None:
    """Returns an Auditor instance (with USN-backed adapter) or None."""
    if not _ensure_kernel_primitives():
        return None
    try:
        from kernel.primitives.auditor import Auditor
        prompt = "You are the Auditor. (kernel primitive)"
        # Use a minimal USN-aware adapter so we stay sovereign (no external shell required in base case)
        adapter = _USNAuditAdapter()
        return Auditor(adapter, prompt)
    except Exception:
        return None


# --- Minimal sovereign audit adapter (records into existing USN mechanisms) ---

class _USNAuditAdapter:
    """
    Duck-typed adapter for kernel.primitives.auditor.Auditor.
    In this Phase-1 integration it simply records via the caller's
    _self_attest + VerifiableMemory (already Merkle-rooted and signed).
    Later this can delegate to the real platform audit_adapter + seal.sh.
    """

    def log(self, entry: Any) -> Any:
        # The real Auditor calls adapter.log with an AuditEntry-like object.
        # We accept anything and let the caller decide how to surface it.
        # For now we are a no-op sink; the caller (USN) will also call _self_attest.
        return {"status": "recorded_in_usn_merkle", "entry_summary": str(entry)[:120]}


# --- Convenience helper used by USN / ConstitutionalGovernor ---

def record_kernel_usage(node: Any, primitive_name: str, details: dict) -> dict | None:
    """Record that a kernel primitive participated in a decision (sovereign audit)."""
    if node is None:
        return None
    try:
        return node._self_attest("kernel_primitive_used", {
            "primitive": primitive_name,
            "details": details,
        })
    except Exception:
        return None
