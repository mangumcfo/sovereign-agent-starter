"""
breathline_primitives.layer5 — Shields (P5)

... (constitutional header same as before)
"""

from __future__ import annotations

import os

__layer__ = "layer5_shields"
__seal_version__ = "v1.0"
__seal_date__ = "2026-01-12"

# Overlay source labels — accurate by construction: the parent package's setup_paths() FAIL-LOUDs on
# an authorized-but-missing overlay BEFORE this module imports, so an "authorized" label here always
# means the overlay actually loaded (the label can never outrun what shadowed the sealed layer).
_merkle_mode = os.environ.get("BREATHLINE_MERKLE_MODE", "sealed").strip().lower()
_zk_mode = os.environ.get("BREATHLINE_ZK_MODE", "sealed").strip().lower()
_merkle_overlay = _merkle_mode in ("authorized-v1.0.1", "v1.0.1", "authorized")
_zk_overlay = _zk_mode in ("authorized-v1.0.2", "v1.0.2", "authorized")

# Merkle (mode-aware — the v1.0.1 overlay shadows merkle_tree.py when active)
from merkle_tree import MerkleTree, hash_function

__merkle_source__ = ("authorized-v1.0.1 (B25 2026-02-05 authorized repair)" if _merkle_overlay
                     else "sealed-v1.0 (pure 2026-01-12 constitutional snapshot)")

# Paillier / WASM — always from the pure seal
from homomorphic_ops import (
    PaillierPublicKey,
    PaillierPrivateKey,
    encrypt,
    decrypt,
    add,
    generate_paillier_keys,
)
# ZK (mode-aware — the v1.0.2 overlay shadows zk_proofs.py when active). In the pure seal ZKProofs
# imports but is non-constructible (HELD); under authorized-v1.0.2 it constructs (Pedersen + Schnorr).
from zk_proofs import ZKProofs
from wasm_runtime import WasmModule

__zk_source__ = ("authorized-v1.0.2 (B25 2026-08-06 authorized repair — Pedersen+Schnorr executable, range HELD)"
                 if _zk_overlay
                 else "sealed-v1.0 (pure 2026-01-12 constitutional snapshot; ZKProofs non-constructible — HELD)")

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
    "__zk_source__",
]
