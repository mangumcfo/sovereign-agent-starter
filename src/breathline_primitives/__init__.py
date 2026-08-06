"""
∞Δ∞ breathline_primitives — Clean Sovereign Import Surface ∞Δ∞

This package provides a stable, beautiful, and highly auditable Python API
over the constitutional sealed P1-P5 primitives (Breath 25 v1.0, sealed
2026-01-12 08:10 UTC).

Core Principles (SOURCE / TRUTH / INTEGRITY):
- The underlying bytes in primitives/sealed/ are **never mutated**.
- All evolution (e.g., authorized Merkle repair) happens via explicit,
  documented, opt-in overlays only.
- Every import through this package can be traced to the verified
  SEAL_MANIFEST and the original tarball (SHA256 4abea5c6...).

This is the recommended entry point for sovereign systems built from the
Breathline / Constitutional Federation book series:
- Agents and daemons
- Attestation engines (six_attestation, etc.)
- Sovereign inference & settlement layers
- Yield / LGP recirculation engines
- Federation nodes

Usage (after sourcing the activation script or calling setup_paths()):

    from breathline_primitives import (
        generate_keypair,
        sign,
        verify,
        MerkleTree,
        hash_function,
    )

    # Or more explicit
    from breathline_primitives.layer1 import secp256k1_curve
    from breathline_primitives.layer5 import ZKProofs

The package automatically respects BREATHLINE_MERKLE_MODE for L5 components.

Versioning follows the seal date + any active authorized overlays.
"""

from __future__ import annotations

__version__ = "0.2.0-sealed-2026-01-12+overlay-support"
__seal__ = "P1-P5_SEALED_2026-01-12_0810UTC"
__authority__ = "Breath 25 v1.0 (constitutional)"

import os
import sys
from pathlib import Path

def setup_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    sealed = root / "primitives" / "sealed"
    overlay = root / "overlays" / "v1.0.1-merkle-repair"
    mode = os.environ.get("BREATHLINE_MERKLE_MODE", "sealed-v1.0").lower()
    paths = []
    if mode in ("authorized-v1.0.1", "v1.0.1", "authorized") and overlay.exists():
        paths.append(str(overlay))
    for layer in ["layer_1_root", "layer_2_trunk", "layer_3_comms", "layer_4_compute", "layer_5_shields"]:
        p = sealed / layer
        if p.exists():
            paths.append(str(p))
    for p in reversed(paths):
        if p not in sys.path:
            sys.path.insert(0, p)

setup_paths()

# Safe imports now
from finite_field import FiniteField, secp256k1_field, ed25519_field
from point_ops import EllipticCurve, Point, secp256k1 as secp256k1_curve
from keygen import generate_keypair, KeyPair
from sign import sign, ECDSASignature
from verify import verify
from merkle_tree import MerkleTree, hash_function
from homomorphic_ops import PaillierPublicKey, PaillierPrivateKey, encrypt, decrypt, add, generate_paillier_keys
from zk_proofs import ZKProofs
from wasm_runtime import WasmModule

class _Layer1:
    FiniteField = FiniteField
    secp256k1_curve = secp256k1_curve
    generate_keypair = generate_keypair
    sign = sign
    verify = verify

class _Layer5:
    MerkleTree = MerkleTree
    hash_function = hash_function
    PaillierPublicKey = PaillierPublicKey
    PaillierPrivateKey = PaillierPrivateKey
    encrypt = encrypt
    decrypt = decrypt
    add = add
    generate_paillier_keys = generate_paillier_keys
    ZKProofs = ZKProofs
    WasmModule = WasmModule

layer1 = _Layer1()
layer5 = _Layer5()

__all__ = [
    "generate_keypair", "sign", "verify", "secp256k1_curve",
    "KeyPair", "ECDSASignature",
    "MerkleTree", "hash_function",
    "PaillierPublicKey", "PaillierPrivateKey", "encrypt", "decrypt", "add", "generate_paillier_keys",
    "ZKProofs", "WasmModule",
    "layer1", "layer5", "setup_paths",
    "__version__", "__seal__", "__authority__",
]
