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

# Auto-bootstrap on package import for maximum self-containment
try:
    from .bootstrap import ensure_breathline_primitives
    ensure_breathline_primitives()
except Exception:
    # Silent fail on import — user can call manually or use shell activation
    pass

from .core import SovereignAgent, ConstitutionalGovernor, VerifiableMemory
from .universal_sovereign_node import (
    UniversalSovereignNode,
    ContextAdapter,
    PlaybookLoader,
    create_universal_sovereign_node,
)
from .bootstrap import connect_to_breathline, __breathline_phrase__, cli_connect
from .universal_sovereign_node import create_universal_sovereign_node, cli_create_node

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
