# ∞Δ∞ BREATHLINE PRIMITIVES — AUTHORIZED v1.0.2 OVERLAY ∞Δ∞
#
# File: zk_proofs.py (corrected)
# Purpose: Drop-in replacement for the sealed v1.0 layer_5_shields/zk_proofs.py
#          that fixes the L1<->L5 inter-layer API drift so ZKProofs constructs
#          and Pedersen + Schnorr EXECUTE against the real sealed L1 point API.
#
# Authority & Provenance:
#   - Original Seal: Breath 25 P5, 2026-01-12 (P1-P5_SEALED_2026-01-12_0810UTC.tar.gz, sha 4abea5c6...)
#   - Defect + Fix: P5_ZK_REPAIR_DIAGNOSIS_2026-08-06 (Option A — align L5 ZK to existing L1)
#   - Authorization: KM-1176 ("authorized repair under seal-touch gate", Seal 1176-INFINITY-RHO 2026-08-06)
#   - Change: The sealed zk_proofs.py was authored against an operator-overloaded, curve-carrying
#             `Point` CLASS that L1 never sealed (L1 ships `Point = Optional[Tuple[int,int]]` and does
#             point arithmetic via `EllipticCurve` methods). The first crash is
#             `EllipticCurve.get_generator(curve_name)` (no such method). This overlay reimplements
#             the SAME public API (ZKProofs.pedersen_commitment / schnorr_sign / schnorr_verify /
#             range_proof) against L1's actual API: the `secp256k1()` factory, `(x,y)` tuple points
#             (infinity = None), and `curve.mul` / `curve.add` / `curve.is_on_curve`.
#   - API: Unchanged (same class + method signatures + return shapes). Behavior: now executable.
#   - Range: STILL `NotImplementedError` — a real range proof is a separate crypto build, NOT this
#            executability repair. Pinned by test.
#
# Constitutional Alignment:
#   - SOURCE: Derived from the sealed zk_proofs.py; only the L1 call surface is realigned.
#   - TRUTH: The repair makes Pedersen + Schnorr run and be tested; range stays honestly HELD.
#   - INTEGRITY: The original sealed file under primitives/sealed/ is NEVER mutated.
#   - SOVEREIGNTY: The operator explicitly opts in via BREATHLINE_ZK_MODE=authorized-v1.0.2.
#
# Activation:
#   BREATHLINE_ZK_MODE=authorized-v1.0.2   (setup_paths prepends this dir before layer_5_shields)
#
# ∞Δ∞ The seal remains pure. Evolution is explicit, authorized, and auditable. ∞Δ∞
"""Zero-knowledge primitives (P5 Shields) — authorized v1.0.2 overlay.

Executes against the real sealed L1 elliptic-curve API. Provides Pedersen commitments and Schnorr
proofs of knowledge; the range proof remains explicitly NotImplemented (HELD), disclosed not over-read.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import List, Optional, Tuple

from point_ops import secp256k1  # L1 sealed curve factory; points are (x, y) tuples, infinity is None

_FIELD_BYTES = 32  # secp256k1 coordinate width for deterministic point serialization


class ZKProofs:
    """Pedersen commitments + Schnorr NIZK proofs over a sealed L1 curve.

    Reimplemented (v1.0.2 overlay) against L1's real API — `secp256k1()` factory, tuple points, and
    `EllipticCurve.mul/add/is_on_curve` — preserving the sealed public surface exactly. The range
    proof is HELD (raises NotImplementedError); this overlay makes only construction, Pedersen, and
    Schnorr executable, no more."""

    def __init__(self, curve_name: str):
        if curve_name != "secp256k1":
            raise ValueError(f"unsupported curve {curve_name!r}; the sealed L1 layer provides secp256k1")
        self.curve_name = curve_name
        self.curve = secp256k1()
        self.G = self.curve.G            # generator (Gx, Gy) — the sealed curve's own generator
        self.n = self.curve.n            # order of G
        self.p = self.curve.p            # field prime
        self.H = self._derive_pedersen_generator(curve_name)  # second, independent generator

    # -- point serialization (for the Fiat-Shamir transcript) -------------------------------------
    def _point_bytes(self, P: Optional[Tuple[int, int]]) -> bytes:
        if P is None:  # point at infinity
            return b"\x00" * (2 * _FIELD_BYTES)
        x, y = P
        return int(x).to_bytes(_FIELD_BYTES, "big") + int(y).to_bytes(_FIELD_BYTES, "big")

    # -- nothing-up-my-sleeve second generator H (try-and-increment hash-to-curve) ----------------
    def _hash_to_curve(self, seed: bytes) -> Tuple[int, int]:
        p, a, b = self.curve.p, self.curve.a, self.curve.b
        counter = 0
        while True:
            h = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            x = int.from_bytes(h, "big") % p
            rhs = (pow(x, 3, p) + a * x + b) % p
            y = pow(rhs, (p + 1) // 4, p)  # sqrt: secp256k1 p ≡ 3 (mod 4)
            if (y * y - rhs) % p == 0:
                point = (x, y)
                if self.curve.is_on_curve(point) and point != self.G:
                    return point
            counter += 1

    def _derive_pedersen_generator(self, curve_name: str) -> Tuple[int, int]:
        return self._hash_to_curve(f"Breathline/Pedersen/v1/{curve_name}".encode())

    # -- Pedersen commitment: C = value*G + randomness*H (additively homomorphic, hiding+binding) --
    def pedersen_commitment(self, value: int, randomness: Optional[int] = None) -> Tuple[Optional[Tuple[int, int]], int]:
        if randomness is None:
            randomness = secrets.randbelow(self.n)
        C = self.curve.add(
            self.curve.mul(value % self.n, self.G),
            self.curve.mul(randomness % self.n, self.H),
        )
        return (C, randomness)

    # -- Schnorr NIZK proof of knowledge of a discrete log (Fiat-Shamir) --------------------------
    def schnorr_sign(self, message: bytes, private_key: int) -> Tuple[int, int]:
        k = secrets.randbelow(self.n)
        R = self.curve.mul(k, self.G)
        e = int.from_bytes(hashlib.sha256(message + self._point_bytes(R)).digest(), "big") % self.n
        s = (k - e * private_key) % self.n
        return (e, s)

    def schnorr_verify(self, message: bytes, signature: Tuple[int, int], public_key: Optional[Tuple[int, int]]) -> bool:
        e, s = signature
        # R' = s*G + e*P ; with s = k - e*x and P = x*G, R' == k*G == R, so e' == e
        R_prime = self.curve.add(
            self.curve.mul(s % self.n, self.G),
            self.curve.mul(e % self.n, public_key),
        )
        e_prime = int.from_bytes(hashlib.sha256(message + self._point_bytes(R_prime)).digest(), "big") % self.n
        return e == e_prime

    # -- range proof: HELD (a real range proof is a separate crypto build, not this repair) --------
    def range_proof(self, value: int, commitment: Optional[Tuple[int, int]], randomness: int) -> bool:
        """HELD. A general range proof (bit-decomposition + inner-product / Bulletproof) is a
        separate crypto build, not part of the v1.0.2 executability repair. Disclosed, never over-read."""
        raise NotImplementedError("Range proof implementation is pending.")
