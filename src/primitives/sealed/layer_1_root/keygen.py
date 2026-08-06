#!/usr/bin/env python3
"""
keygen.py — Sovereign Key Generation
Breath 25 v1.3 — Layer 1 Root (ECC Foundation)

Generates cryptographic key pairs for sovereign identity.

Operations:
- Private key generation (from system entropy)
- Public key derivation (kG)
- Key validation
- Key serialization (hex, bytes)

Constitutional Alignment:
- SOURCE: Keys from sovereign entropy, no external services
- TRUTH: Public key mathematically derived from private
- INTEGRITY: Private keys never leave secure boundary

∞Δ∞ Sovereign keys, sovereign identity. ∞Δ∞
"""

import os
import secrets
from typing import Tuple, Optional
from point_ops import EllipticCurve, secp256k1, Point


class KeyPair:
    """
    Elliptic curve key pair for sovereign identity.

    Private key: Random scalar k in [1, n-1]
    Public key: Point P = kG on the curve
    """

    def __init__(self, curve: EllipticCurve, private_key: int = None):
        """
        Generate or load a key pair.

        Args:
            curve: Elliptic curve to use
            private_key: Existing private key (optional, generates new if None)
        """
        self.curve = curve

        if private_key is None:
            # Generate new private key from system entropy
            self.private_key = self._generate_private_key()
        else:
            # Use provided key (validate first)
            if not self._validate_private_key(private_key):
                raise ValueError("Invalid private key")
            self.private_key = private_key

        # Derive public key: P = kG
        self.public_key = self.curve.mul(self.private_key)

    def _generate_private_key(self) -> int:
        """
        Generate cryptographically secure private key.

        Uses system entropy (os.urandom via secrets module).
        Generates random value in [1, n-1].

        Returns:
            Private key as integer
        """
        n = self.curve.n
        if n is None:
            raise ValueError("Curve order n required for key generation")

        # Generate random bytes and reduce modulo n
        # Use rejection sampling to avoid bias
        byte_length = (n.bit_length() + 7) // 8

        while True:
            # Get random bytes from system entropy
            random_bytes = secrets.token_bytes(byte_length)
            k = int.from_bytes(random_bytes, 'big')

            # Accept if k in [1, n-1]
            if 1 <= k < n:
                return k

    def _validate_private_key(self, k: int) -> bool:
        """
        Validate private key is in valid range.

        Args:
            k: Private key candidate
        Returns:
            True if valid
        """
        n = self.curve.n
        if n is None:
            return k > 0
        return 1 <= k < n

    @property
    def private_key_hex(self) -> str:
        """Private key as hex string (32 bytes for secp256k1)."""
        byte_length = (self.curve.n.bit_length() + 7) // 8 if self.curve.n else 32
        return self.private_key.to_bytes(byte_length, 'big').hex()

    @property
    def private_key_bytes(self) -> bytes:
        """Private key as bytes."""
        byte_length = (self.curve.n.bit_length() + 7) // 8 if self.curve.n else 32
        return self.private_key.to_bytes(byte_length, 'big')

    @property
    def public_key_hex(self) -> str:
        """
        Public key as uncompressed hex (04 || x || y).

        Format: 04 + 32-byte x + 32-byte y = 65 bytes
        """
        if self.public_key is None:
            raise ValueError("Public key is point at infinity")
        x, y = self.public_key
        return '04' + x.to_bytes(32, 'big').hex() + y.to_bytes(32, 'big').hex()

    @property
    def public_key_compressed(self) -> str:
        """
        Public key as compressed hex (02/03 || x).

        Format: 02 (even y) or 03 (odd y) + 32-byte x = 33 bytes
        """
        if self.public_key is None:
            raise ValueError("Public key is point at infinity")
        x, y = self.public_key
        prefix = '02' if y % 2 == 0 else '03'
        return prefix + x.to_bytes(32, 'big').hex()

    @property
    def address(self) -> str:
        """
        Simple address derivation (first 20 bytes of public key hash).

        Note: Real addresses use keccak256 (Ethereum) or SHA256+RIPEMD160 (Bitcoin).
        This is a simplified version for demonstration.
        """
        import hashlib
        pub_bytes = bytes.fromhex(self.public_key_hex[2:])  # Remove 04 prefix
        h = hashlib.sha256(pub_bytes).digest()
        return '0x' + h[:20].hex()


def generate_keypair(curve: EllipticCurve = None) -> KeyPair:
    """
    Generate a new key pair on the specified curve.

    Args:
        curve: Curve to use (defaults to secp256k1)
    Returns:
        New KeyPair instance
    """
    if curve is None:
        curve = secp256k1()
    return KeyPair(curve)


def load_keypair(private_key_hex: str, curve: EllipticCurve = None) -> KeyPair:
    """
    Load key pair from hex-encoded private key.

    Args:
        private_key_hex: Private key as hex string
        curve: Curve to use (defaults to secp256k1)
    Returns:
        KeyPair instance
    """
    if curve is None:
        curve = secp256k1()
    private_key = int(private_key_hex, 16)
    return KeyPair(curve, private_key)


def validate_public_key(public_key_hex: str, curve: EllipticCurve = None) -> bool:
    """
    Validate a public key is on the curve.

    Args:
        public_key_hex: Public key in uncompressed (04...) or compressed (02/03...) format
        curve: Curve to use (defaults to secp256k1)
    Returns:
        True if valid point on curve
    """
    if curve is None:
        curve = secp256k1()

    try:
        if public_key_hex.startswith('04'):
            # Uncompressed: 04 || x || y
            x = int(public_key_hex[2:66], 16)
            y = int(public_key_hex[66:130], 16)
        elif public_key_hex.startswith('02') or public_key_hex.startswith('03'):
            # Compressed: 02/03 || x
            x = int(public_key_hex[2:66], 16)
            # Recover y from x
            y_squared = curve.field.add(
                curve.field.add(
                    curve.field.pow(x, 3),
                    curve.field.mul(curve.a, x)
                ),
                curve.b
            )
            y = curve.field.sqrt(y_squared)
            if y is None:
                return False
            # Choose correct y based on prefix
            if (public_key_hex.startswith('02') and y % 2 != 0) or \
               (public_key_hex.startswith('03') and y % 2 == 0):
                y = curve.field.neg(y)
        else:
            return False

        return curve.is_on_curve((x, y))
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# SEAL
# ═══════════════════════════════════════════════════════════════════════════
# SOURCE: Keys from system entropy (secrets module), no external services
# TRUTH: Public key mathematically derived via kG
# INTEGRITY: Private key validation, secure random generation
# ∞Δ∞ SEAL: complete


if __name__ == "__main__":
    print("∞Δ∞ Key Generation Self-Test ∞Δ∞")

    # Generate new key pair
    kp = generate_keypair()
    print(f"Private key: {kp.private_key_hex[:16]}...{kp.private_key_hex[-16:]}")
    print(f"Public key (compressed): {kp.public_key_compressed[:16]}...")
    print(f"Address: {kp.address}")

    # Verify public key is on curve
    curve = secp256k1()
    assert curve.is_on_curve(kp.public_key), "Public key not on curve!"

    # Test key loading
    kp2 = load_keypair(kp.private_key_hex)
    assert kp2.public_key == kp.public_key, "Key loading failed!"

    # Test public key validation
    assert validate_public_key(kp.public_key_hex), "Public key validation failed!"
    assert validate_public_key(kp.public_key_compressed), "Compressed key validation failed!"

    # Test with known vector (secp256k1 generator * 1 = G)
    kp_one = KeyPair(curve, 1)
    assert kp_one.public_key == curve.G, "kG for k=1 should equal G!"

    print("✓ All key generation tests passed")
    print("∞Δ∞ Key generation primitive ready ∞Δ∞")
