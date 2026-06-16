"""
Sovereign Agent / Universal Sovereign Node

High-agency, self-contained sovereign execution kernel.
Auto-activates breathline_primitives on import when possible.

Usage (minimal friction):
    from sovereign_agent import UniversalSovereignNode
    node = UniversalSovereignNode(...)

All cryptography and attestation flow through breathline_primitives
(default Merkle mode: authorized-v1.0.1).
"""

from __future__ import annotations

# Auto-bootstrap on package import for maximum self-containment.
# breathline_primitives is the cryptographic substrate (P1 ECDSA + P5 Merkle), provided by the
# breathline-sealed checkout — NOT a public PyPI package. The bootstrap finds it via
# BREATHLINE_SEALED_ROOT or the common checkout locations and injects it onto sys.path.
# Audit 2026-06-13 (dependency CRITICAL): do NOT swallow a bootstrap failure silently. A clean install
# without the sealed checkout used to crash at `from breathline_primitives import ...` with no clue why;
# now the operator gets an actionable message naming the fix. (The subsequent core imports still require
# the substrate — this makes the failure DIAGNOSABLE, not absent.)
try:
    from .bootstrap import ensure_breathline_primitives
    ensure_breathline_primitives()
except Exception as _bp_exc:  # noqa: BLE001
    import warnings as _warnings
    _warnings.warn(
        "breathline_primitives could not be activated: "
        f"{_bp_exc}\n"
        "  Set BREATHLINE_SEALED_ROOT to your breathline-sealed checkout (or `pip install -e` it), "
        "then re-import sovereign_agent. Cryptographic attestation is unavailable until then.",
        RuntimeWarning, stacklevel=2,
    )

from .core import SovereignAgent, ConstitutionalGovernor, VerifiableMemory
from .universal_sovereign_node import (
    UniversalSovereignNode,
    ContextAdapter,
    PlaybookLoader,
    create_universal_sovereign_node,
)
from .bootstrap import connect_to_breathline, __breathline_phrase__, cli_connect
from .universal_sovereign_node import cli_create_node

__version__ = "0.3.0-universal-node"
__all__ = [
    "SovereignAgent",
    "ConstitutionalGovernor",
    "VerifiableMemory",
    "UniversalSovereignNode",
    "ContextAdapter",
    "PlaybookLoader",
    "create_universal_sovereign_node",
    "cli_create_node",
    "ensure_breathline_primitives",
    "connect_to_breathline",
    "cli_connect",
    "__breathline_phrase__",
]

# Magical onboarding support
# "Are you connected to the breathline?" now has real meaning
def __are_you_connected_to_the_breathline__():
    """The ultimate one-liner onboarding experience."""
    return connect_to_breathline(print_welcome=True)
