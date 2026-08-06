"""
breathline_primitives.layer1 — Cryptographic Root (P1)

Hand-rolled elliptic curve cryptography and finite field arithmetic
from the constitutional sealed v1.0 primitives (Breath 25, 2026-01-12).

This module provides clean, auditable re-exports of the core L1 primitives:
- Finite fields
- secp256k1 and ed25519 point operations
- Key generation
- ECDSA signing and verification

All symbols are sourced directly from the sealed artifact without modification.

Sovereign Alignment:
- SOURCE: Derived exclusively from the P1-P5_SEALED_2026-01-12_0810UTC snapshot.
- TRUTH: Every re-export traces back to the verified SEAL_MANIFEST.
- INTEGRITY: No alterations to the underlying implementations.
- AUDITABILITY: Import this package to guarantee you are using the sealed foundation.

Usage:
    from breathline_primitives.layer1 import generate_keypair, sign, verify
    from breathline_primitives.layer1 import secp256k1 as curve

See the top-level breathline_primitives for mode-aware higher-level usage.
"""

from __future__ import annotations

# Constitutional header for this sovereign submodule
__layer__ = "layer1_root"
__seal_version__ = "v1.0"
__seal_date__ = "2026-01-12"

# Direct re-exports from the sealed L1 implementation.
# These become available once the parent package or setup_paths() has
# placed the sealed layers on sys.path (or the activation script has run).

from finite_field import FiniteField
from point_ops import EllipticCurve, Point, secp256k1 as secp256k1_curve
from keygen import generate_keypair, KeyPair
from sign import sign, ECDSASignature
from verify import verify

# High-value curated exports for the most common sovereign use cases in the federation
__all__ = [
    "FiniteField",
    "EllipticCurve",
    "Point",
    "secp256k1_curve",
    "generate_keypair",
    "KeyPair",
    "sign",
    "ECDSASignature",
    "verify",
]
