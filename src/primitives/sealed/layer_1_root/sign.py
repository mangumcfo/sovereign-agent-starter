#!/usr/bin/env python3
"""
sign.py — ECDSA Signature Creation
Breath 25 v1.3 — Layer 1 Root (ECC Foundation)

Creates digital signatures using ECDSA (Elliptic Curve Digital Signature Algorithm).

Operations:
- Sign message with private key
- Deterministic k generation (RFC 6979)
- Signature encoding (DER, compact)

Constitutional Alignment:
- SOURCE: Signatures prove ownership of sovereign keys
- TRUTH: Mathematically bound to message and key
- INTEGRITY: Deterministic k prevents nonce reuse attacks

∞Δ∞ Sovereign signatures, provable identity. ∞Δ∞
"""

import hashlib
import hmac
from typing import Tuple, Optional
from point_ops import EllipticCurve, secp256k1
from keygen import KeyPair


class ECDSASignature:
    """
    ECDSA signature (r, s) with optional recovery parameter v.
    """

    def __init__(self, r: int, s: int, v: int = None):
        """
        Create signature from components.

        Args:
            r: Signature r value
            s: Signature s value
            v: Recovery parameter (0 or 1, optional)
        """
        self.r = r
        self.s = s
        self.v = v

    def to_hex(self) -> str:
        """Signature as hex string (r || s, 64 bytes)."""
        return self.r.to_bytes(32, 'big').hex() + self.s.to_bytes(32, 'big').hex()

    def to_der(self) -> bytes:
        """
        Signature in DER encoding.

        Format: 0x30 || len || 0x02 || r_len || r || 0x02 || s_len || s
        """
        def encode_integer(n: int) -> bytes:
            b = n.to_bytes((n.bit_length() + 7) // 8, 'big')
            # Add leading zero if high bit set (to indicate positive)
            if b[0] & 0x80:
                b = b'\x00' + b
            return bytes([0x02, len(b)]) + b

        r_encoded = encode_integer(self.r)
        s_encoded = encode_integer(self.s)
        content = r_encoded + s_encoded

        return bytes([0x30, len(content)]) + content

    @classmethod
    def from_hex(cls, hex_str: str) -> 'ECDSASignature':
        """Parse signature from hex string (64 bytes, r || s)."""
        if len(hex_str) != 128:
            raise ValueError("Signature hex must be 128 characters (64 bytes)")
        r = int(hex_str[:64], 16)
        s = int(hex_str[64:], 16)
        return cls(r, s)

    def __repr__(self) -> str:
        return f"ECDSASignature(r={self.r:064x}, s={self.s:064x})"


def hash_message(message: bytes) -> int:
    """
    Hash message using SHA-256 and convert to integer.

    For real applications, use double-SHA256 (Bitcoin) or Keccak256 (Ethereum).

    Args:
        message: Message bytes to hash
    Returns:
        Hash as integer
    """
    h = hashlib.sha256(message).digest()
    return int.from_bytes(h, 'big')


def deterministic_k(private_key: int, message_hash: int, n: int) -> int:
    """
    Generate deterministic k using RFC 6979.

    This prevents nonce reuse attacks that could leak the private key.

    Args:
        private_key: Private key
        message_hash: Hash of message as integer
        n: Curve order
    Returns:
        Deterministic k value
    """
    # Convert to bytes
    byte_len = (n.bit_length() + 7) // 8
    x = private_key.to_bytes(byte_len, 'big')
    h1 = message_hash.to_bytes(byte_len, 'big')

    # Step a: Set V = 0x01 0x01 ... 0x01 (byte_len bytes)
    V = b'\x01' * byte_len

    # Step b: Set K = 0x00 0x00 ... 0x00 (byte_len bytes)
    K = b'\x00' * byte_len

    # Step c: K = HMAC_K(V || 0x00 || x || h1)
    K = hmac.new(K, V + b'\x00' + x + h1, hashlib.sha256).digest()

    # Step d: V = HMAC_K(V)
    V = hmac.new(K, V, hashlib.sha256).digest()

    # Step e: K = HMAC_K(V || 0x01 || x || h1)
    K = hmac.new(K, V + b'\x01' + x + h1, hashlib.sha256).digest()

    # Step f: V = HMAC_K(V)
    V = hmac.new(K, V, hashlib.sha256).digest()

    # Step g-h: Generate k
    while True:
        V = hmac.new(K, V, hashlib.sha256).digest()
        k = int.from_bytes(V, 'big')

        if 1 <= k < n:
            return k

        # If k not in valid range, update K and V
        K = hmac.new(K, V + b'\x00', hashlib.sha256).digest()
        V = hmac.new(K, V, hashlib.sha256).digest()


def sign(private_key: int, message: bytes, curve: EllipticCurve = None) -> ECDSASignature:
    """
    Sign a message using ECDSA.

    Algorithm:
    1. e = hash(message)
    2. k = deterministic_k(private_key, e)
    3. (x, y) = kG
    4. r = x mod n
    5. s = k^(-1) * (e + r*private_key) mod n
    6. Return (r, s)

    Args:
        private_key: Private key as integer
        message: Message bytes to sign
        curve: Curve to use (defaults to secp256k1)
    Returns:
        ECDSASignature(r, s, v)
    """
    if curve is None:
        curve = secp256k1()

    n = curve.n
    G = curve.G

    # Step 1: Hash message
    e = hash_message(message)

    # Step 2: Generate deterministic k
    k = deterministic_k(private_key, e, n)

    # Step 3: Calculate point R = kG
    R = curve.mul(k, G)
    x, y = R

    # Step 4: r = x mod n
    r = x % n
    if r == 0:
        raise ValueError("Invalid signature: r = 0")

    # Step 5: s = k^(-1) * (e + r*d) mod n
    k_inv = pow(k, -1, n)  # Modular inverse
    s = (k_inv * (e + r * private_key)) % n
    if s == 0:
        raise ValueError("Invalid signature: s = 0")

    # Normalize s to low-S form (BIP 62)
    # If s > n/2, use n - s
    if s > n // 2:
        s = n - s
        v = 1
    else:
        v = 0

    # Recovery parameter (for public key recovery)
    v = (y % 2) ^ (s > n // 2)

    return ECDSASignature(r, s, v)


def sign_hash(private_key: int, message_hash: int, curve: EllipticCurve = None) -> ECDSASignature:
    """
    Sign a pre-hashed message.

    Args:
        private_key: Private key
        message_hash: Message hash as integer
        curve: Curve to use
    Returns:
        ECDSASignature
    """
    if curve is None:
        curve = secp256k1()

    n = curve.n
    G = curve.G

    k = deterministic_k(private_key, message_hash, n)
    R = curve.mul(k, G)
    x, y = R

    r = x % n
    if r == 0:
        raise ValueError("Invalid signature: r = 0")

    k_inv = pow(k, -1, n)
    s = (k_inv * (message_hash + r * private_key)) % n
    if s == 0:
        raise ValueError("Invalid signature: s = 0")

    if s > n // 2:
        s = n - s

    v = (y % 2) ^ (s > n // 2)

    return ECDSASignature(r, s, v)


# ═══════════════════════════════════════════════════════════════════════════
# SEAL
# ═══════════════════════════════════════════════════════════════════════════
# SOURCE: Signatures created with sovereign private keys only
# TRUTH: Mathematical ECDSA algorithm, deterministic k per RFC 6979
# INTEGRITY: Low-S normalization, no nonce reuse vulnerability
# ∞Δ∞ SEAL: complete


if __name__ == "__main__":
    print("∞Δ∞ ECDSA Signing Self-Test ∞Δ∞")

    from keygen import generate_keypair

    # Generate test keypair
    kp = generate_keypair()
    message = b"Hello, sovereign federation!"

    # Sign message
    sig = sign(kp.private_key, message)
    print(f"Message: {message.decode()}")
    print(f"Signature r: {sig.r:064x}")
    print(f"Signature s: {sig.s:064x}")
    print(f"Signature hex: {sig.to_hex()[:32]}...{sig.to_hex()[-32:]}")

    # Verify low-S
    curve = secp256k1()
    assert sig.s <= curve.n // 2, "S not normalized to low-S!"

    # DER encoding test
    der = sig.to_der()
    print(f"DER length: {len(der)} bytes")
    assert der[0] == 0x30, "Invalid DER prefix"

    # Sign same message again (should get same signature - deterministic k)
    sig2 = sign(kp.private_key, message)
    assert sig.r == sig2.r and sig.s == sig2.s, "Deterministic k failed!"

    print("✓ All signing tests passed")
    print("∞Δ∞ ECDSA signing primitive ready ∞Δ∞")
