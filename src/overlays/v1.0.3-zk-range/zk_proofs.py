# ∞Δ∞ BREATHLINE PRIMITIVES — AUTHORIZED v1.0.3 OVERLAY ∞Δ∞
#
# File: zk_proofs.py (corrected + range)
# Purpose: Supersedes the v1.0.2 overlay. In addition to making ZKProofs construct and Pedersen +
#          Schnorr execute against the real sealed L1 API (v1.0.2), this overlay implements a correct,
#          sound RANGE PROOF (bit-decomposition + Schnorr-OR) — replacing the NotImplementedError.
#
# Authority & Provenance:
#   - Original Seal: Breath 25 P5, 2026-01-12 (P1-P5_SEALED_2026-01-12_0810UTC.tar.gz, sha 4abea5c6...)
#   - Repairs: v1.0.2 (Option A L1-alignment) + v1.0.3 (range proof), P5 shield capacity Task Force.
#   - Authorization: KM-1176 seal-touch (Seal 1176-INFINITY-RHO, 2026-08-06, W1).
#   - Construction: range_proof proves value ∈ [0, 2^bits) with NO reveal — commit each bit (Pedersen),
#     prove each bit ∈ {0,1} via a Fiat-Shamir Schnorr OR-proof, and bind Σ 2^i·C_i == C. Built ONLY
#     from primitives already PRESENT (Pedersen + Schnorr over the sealed L1 curve). No new L1.
#   - API: pedersen_commitment / schnorr_sign / schnorr_verify unchanged from v1.0.2. range_proof now
#     RETURNS a proof object (was NotImplementedError); verify_range_proof(commitment, proof) checks it.
#
# Constitutional Alignment:
#   - INTEGRITY: the original sealed file under primitives/sealed/ is NEVER mutated.
#   - TRUTH: range is now executable AND sound (out-of-range and tampered proofs reject) — tested.
#   - SOVEREIGNTY: opt-in via BREATHLINE_ZK_MODE=authorized-v1.0.3 (supersedes v1.0.2).
#
# ∞Δ∞ The seal remains pure. Evolution is explicit, authorized, and auditable. ∞Δ∞
"""Zero-knowledge primitives (P5 Shields) — authorized v1.0.3 overlay (Pedersen + Schnorr + Range).

Range proof: bit-decomposition with per-bit Schnorr-OR (0-or-1) proofs, bound to the commitment by the
homomorphic sum Σ 2^i·C_i == C. Proves value ∈ [0, 2^bits) without revealing it; a threshold "v ≥ m"
is the range proof on the difference commitment C − m·G.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Dict, List, Optional, Tuple

from point_ops import secp256k1  # L1 sealed curve factory; points are (x, y) tuples, infinity is None

_FIELD_BYTES = 32
_DEFAULT_BITS = 32


class ZKProofs:
    """Pedersen commitments + Schnorr NIZK proofs + a sound bit-decomposition range proof, over the
    sealed L1 curve. v1.0.3 overlay — supersedes v1.0.2 (adds range)."""

    def __init__(self, curve_name: str):
        if curve_name != "secp256k1":
            raise ValueError(f"unsupported curve {curve_name!r}; the sealed L1 layer provides secp256k1")
        self.curve_name = curve_name
        self.curve = secp256k1()
        self.G = self.curve.G
        self.n = self.curve.n
        self.p = self.curve.p
        self.H = self._derive_pedersen_generator(curve_name)

    # -- point serialization / transcript ---------------------------------------------------------
    def _point_bytes(self, P: Optional[Tuple[int, int]]) -> bytes:
        if P is None:
            return b"\x00" * (2 * _FIELD_BYTES)
        x, y = P
        return int(x).to_bytes(_FIELD_BYTES, "big") + int(y).to_bytes(_FIELD_BYTES, "big")

    def _challenge(self, *points: Optional[Tuple[int, int]], tag: bytes = b"") -> int:
        h = hashlib.sha256(tag + b"".join(self._point_bytes(P) for P in points)).digest()
        return int.from_bytes(h, "big") % self.n

    # -- nothing-up-my-sleeve second generator H --------------------------------------------------
    def _hash_to_curve(self, seed: bytes) -> Tuple[int, int]:
        p, a, b = self.curve.p, self.curve.a, self.curve.b
        counter = 0
        while True:
            hsh = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            x = int.from_bytes(hsh, "big") % p
            rhs = (pow(x, 3, p) + a * x + b) % p
            y = pow(rhs, (p + 1) // 4, p)  # sqrt: secp256k1 p ≡ 3 (mod 4)
            if (y * y - rhs) % p == 0:
                point = (x, y)
                if self.curve.is_on_curve(point) and point != self.G:
                    return point
            counter += 1

    def _derive_pedersen_generator(self, curve_name: str) -> Tuple[int, int]:
        return self._hash_to_curve(f"Breathline/Pedersen/v1/{curve_name}".encode())

    # -- Pedersen commitment ----------------------------------------------------------------------
    def pedersen_commitment(self, value: int, randomness: Optional[int] = None) -> Tuple[Optional[Tuple[int, int]], int]:
        if randomness is None:
            randomness = secrets.randbelow(self.n)
        C = self.curve.add(
            self.curve.mul(value % self.n, self.G),
            self.curve.mul(randomness % self.n, self.H),
        )
        return (C, randomness)

    # -- Schnorr NIZK proof of knowledge of a discrete log ----------------------------------------
    def schnorr_sign(self, message: bytes, private_key: int) -> Tuple[int, int]:
        k = secrets.randbelow(self.n)
        R = self.curve.mul(k, self.G)
        e = int.from_bytes(hashlib.sha256(message + self._point_bytes(R)).digest(), "big") % self.n
        s = (k - e * private_key) % self.n
        return (e, s)

    def schnorr_verify(self, message: bytes, signature: Tuple[int, int], public_key: Optional[Tuple[int, int]]) -> bool:
        e, s = signature
        R_prime = self.curve.add(self.curve.mul(s % self.n, self.G), self.curve.mul(e % self.n, public_key))
        e_prime = int.from_bytes(hashlib.sha256(message + self._point_bytes(R_prime)).digest(), "big") % self.n
        return e == e_prime

    # -- bit OR-proof: prove a commitment Ci = b*G + ri*H has b ∈ {0,1} (Fiat-Shamir Schnorr-OR) ---
    # Statement branches over base H: P0 = Ci (knows ri s.t. Ci = ri*H when b=0);
    #                                 P1 = Ci - G (knows ri s.t. Ci - G = ri*H when b=1).
    def _bit_or_proof(self, Ci, bit: int, ri: int, idx: int) -> Dict:
        H, n = self.H, self.n
        P0 = Ci
        P1 = self.curve.add(Ci, self.curve.neg(self.G))
        tag = b"BLRANGE/bit/" + idx.to_bytes(2, "big")
        if bit == 0:
            k = secrets.randbelow(n)
            A0 = self.curve.mul(k, H)                         # real branch commitment
            e1 = secrets.randbelow(n)                          # simulate branch 1
            s1 = secrets.randbelow(n)
            A1 = self.curve.add(self.curve.mul(s1, H), self.curve.neg(self.curve.mul(e1, P1)))
            e = self._challenge(P0, A0, A1, tag=tag)
            e0 = (e - e1) % n
            s0 = (k + e0 * ri) % n
        else:
            k = secrets.randbelow(n)
            A1 = self.curve.mul(k, H)                          # real branch commitment
            e0 = secrets.randbelow(n)                          # simulate branch 0
            s0 = secrets.randbelow(n)
            A0 = self.curve.add(self.curve.mul(s0, H), self.curve.neg(self.curve.mul(e0, P0)))
            e = self._challenge(P0, A0, A1, tag=tag)
            e1 = (e - e0) % n
            s1 = (k + e1 * ri) % n
        return {"A0": A0, "A1": A1, "e0": e0, "e1": e1, "s0": s0, "s1": s1}

    def _verify_bit_or(self, Ci, proof: Dict, idx: int) -> bool:
        H, n = self.H, self.n
        P0 = Ci
        P1 = self.curve.add(Ci, self.curve.neg(self.G))
        A0, A1 = proof["A0"], proof["A1"]
        e0, e1, s0, s1 = proof["e0"] % n, proof["e1"] % n, proof["s0"] % n, proof["s1"] % n
        tag = b"BLRANGE/bit/" + idx.to_bytes(2, "big")
        e = self._challenge(P0, A0, A1, tag=tag)
        if (e0 + e1) % n != e:                                 # challenge split must sum to the FS challenge
            return False
        # s0*H == A0 + e0*P0  and  s1*H == A1 + e1*P1
        chk0 = self.curve.mul(s0, H) == self.curve.add(A0, self.curve.mul(e0, P0))
        chk1 = self.curve.mul(s1, H) == self.curve.add(A1, self.curve.mul(e1, P1))
        return bool(chk0 and chk1)

    # -- range proof: value ∈ [0, 2^bits), no reveal ----------------------------------------------
    def range_proof(self, value: int, commitment, randomness: int, *, bits: int = _DEFAULT_BITS) -> Dict:
        """Prove `value ∈ [0, 2^bits)` for the Pedersen `commitment = value*G + randomness*H` without
        revealing value. Returns a proof {bits, C, bit_commitments, bit_proofs}. Refuses a value that
        is not representable in `bits` (an honest prover cannot prove a false range)."""
        n = self.n
        if value < 0 or value >= (1 << bits):
            raise ValueError(f"value {value} is not in [0, 2^{bits}) — no honest range proof exists")
        # blind each bit so that Σ 2^i r_i == randomness  (=> Σ 2^i C_i == commitment)
        r_bits: List[int] = [secrets.randbelow(n) for _ in range(bits - 1)]
        partial = sum((1 << i) * r_bits[i] for i in range(bits - 1)) % n
        inv_last = pow(1 << (bits - 1), -1, n)
        r_bits.append(((randomness - partial) % n) * inv_last % n)
        C_bits, bit_proofs = [], []
        for i in range(bits):
            b = (value >> i) & 1
            Ci = self.curve.add(self.curve.mul(b, self.G), self.curve.mul(r_bits[i] % n, self.H))
            C_bits.append(Ci)
            bit_proofs.append(self._bit_or_proof(Ci, b, r_bits[i] % n, i))
        return {"bits": bits, "C": commitment, "bit_commitments": C_bits, "bit_proofs": bit_proofs}

    def verify_range_proof(self, commitment, proof: Dict, *, bits: Optional[int] = None) -> bool:
        """Verify a range proof against `commitment`. Sound: rejects out-of-range (a bit proof fails or
        the homomorphic sum ≠ commitment) and any tampered proof element."""
        try:
            b = proof["bits"] if bits is None else bits
            C_bits = proof["bit_commitments"]
            bit_proofs = proof["bit_proofs"]
            if len(C_bits) != b or len(bit_proofs) != b:
                return False
            # 1) every bit commitment opens to 0 or 1
            for i in range(b):
                if not self._verify_bit_or(C_bits[i], bit_proofs[i], i):
                    return False
            # 2) the bits bind to the commitment: Σ 2^i · C_i == commitment
            acc = None
            for i in range(b):
                acc = self.curve.add(acc, self.curve.mul(1 << i, C_bits[i]))
            return acc == commitment
        except (KeyError, TypeError, ValueError):
            return False
