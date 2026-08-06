"""
breathline_primitives.layer5 — Shields (P5)

... (constitutional header same as before)
"""

from __future__ import annotations

import os

__layer__ = "layer5_shields"
__seal_version__ = "v1.0"
__seal_date__ = "2026-01-12"

_mode = os.environ.get("BREATHLINE_MERKLE_MODE", "sealed-v1.0").lower()
_use_overlay = _mode in ("authorized-v1.0.1", "v1.0.1", "authorized")

# Merkle (mode-aware)
from merkle_tree import MerkleTree, hash_function

if _use_overlay:
    __merkle_source__ = "authorized-v1.0.1 (B25 2026-02-05 authorized repair)"
else:
    __merkle_source__ = "sealed-v1.0 (pure 2026-01-12 constitutional snapshot)"

# Other L5 components (always from pure seal)
from homomorphic_ops import (
    PaillierPublicKey,
    PaillierPrivateKey,
    encrypt,
    decrypt,
    add,
    generate_paillier_keys,
)
from zk_proofs import ZKProofs
from wasm_runtime import WasmModule

__all__ = [
    "MerkleTree",
    "hash_function",
    "PaillierPublicKey",
    "PaillierPrivateKey",
    "encrypt",
    "decrypt",
    "add",
    "generate_paillier_keys",
    "ZKProofs",
    "WasmModule",
    "__merkle_source__",
]
