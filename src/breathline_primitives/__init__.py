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

# Authorized repair overlays (opt-in ONLY; sealed originals under primitives/sealed/ are NEVER mutated).
# Each entry: the env var that opts in, the values that count as authorized, the overlay directory, and
# the label that must match what actually loaded. FAIL-LOUD (KM-1176, Seal 1176-INFINITY-RHO 2026-08-06):
# an authorized mode whose overlay dir is MISSING RAISES, rather than silently loading the sealed original
# under an authorized label.
_OVERLAYS = (
    {"env": "BREATHLINE_MERKLE_MODE", "authorized": ("authorized-v1.0.1", "v1.0.1", "authorized"),
     "dir": "v1.0.1-merkle-repair", "label": "authorized-v1.0.1"},
    {"env": "BREATHLINE_ZK_MODE", "authorized": ("authorized-v1.0.2", "v1.0.2", "authorized"),
     "dir": "v1.0.2-zk-repair", "label": "authorized-v1.0.2"},
)


def active_overlays(root=None):
    """[(env, label, dir_path)] for every overlay the operator opted into. FAIL-LOUD if an authorized
    mode is requested but its overlay directory is missing — the label can never outrun what loaded.
    `root` defaults to the substrate root (the dir holding overlays/ and primitives/); tests pass one."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    active = []
    for ov in _OVERLAYS:
        mode = os.environ.get(ov["env"], "sealed").strip().lower()
        if mode in ov["authorized"]:
            d = root / "overlays" / ov["dir"]
            if not d.is_dir():
                raise RuntimeError(
                    f"BREATHLINE overlay FAIL-LOUD: {ov['env']}={mode!r} requests the "
                    f"'{ov['label']}' authorized overlay, but {d} is MISSING. Refusing to load the "
                    f"sealed original under an authorized label — vendor the overlay directory or unset "
                    f"{ov['env']}.")
            active.append((ov["env"], ov["label"], d))
    return active


def overlay_label(env: str) -> str:
    """The source label for an overlay-gated component: its authorized label if active, else the pure
    seal. Guaranteed accurate — active_overlays() fail-louds before this can mislabel."""
    for e, label, _ in active_overlays():
        if e == env:
            return label
    return "sealed-v1.0 (pure 2026-01-12 constitutional snapshot)"


def setup_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    sealed = root / "primitives" / "sealed"
    paths = [str(d) for _, _, d in active_overlays()]  # overlays first — they shadow the sealed layer
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
