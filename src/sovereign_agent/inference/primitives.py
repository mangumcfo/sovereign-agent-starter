"""
Sealed-primitives adapter (TA-1 path (a), KM 2026-06-11).

Wires the Vol 1 trust layer to the REAL sealed stack — P1 ECDSA (secp256k1) signing + P5 Merkle — from the
`breathline-sealed` repository the book points readers at, when it is present. Falls back to stdlib hashlib
so the modules still run anywhere (demo mode, no sealed clone). `using_sealed()` reports which substrate is
live — honest about whether a receipt is P1-*signed* or only hash-bound.

Book ↔ code (Tech/Arch TA-1): this closes the substrate gap — receipts now hash via the sealed
`hash_function`, chain via the sealed `MerkleTree`, and carry a real P1 ECDSA signature when an operator
identity key is supplied. The same primitives a reader verifies with `bl-verify`.
"""
from __future__ import annotations

import hashlib
from typing import Optional

_BP = None  # None=unprobed, False=absent, module=present


def _bp():
    global _BP
    if _BP is not None:
        return _BP or None
    try:
        import breathline_primitives as bp  # noqa: PLC0415
        _BP = bp
        return bp
    except ImportError:
        pass
    try:
        from .. import config  # noqa: PLC0415
        root = config.get_sealed_root()
        if root:
            import sys  # noqa: PLC0415
            p = str(root)
            if p not in sys.path:
                sys.path.insert(0, p)
            import breathline_primitives as bp  # noqa: PLC0415
            _BP = bp
            return bp
    except Exception:  # noqa: BLE001
        pass
    _BP = False
    return None


def using_sealed() -> bool:
    """True iff the sealed breathline-sealed primitives are live (else stdlib fallback)."""
    return _bp() is not None


def _b(data) -> bytes:
    return data.encode("utf-8") if isinstance(data, str) else data


def sealed_hash(data) -> str:
    """SHA-256 via the sealed P-layer hash_function when present (else stdlib) — same digest, sealed path."""
    bp = _bp()
    digest = bp.hash_function(_b(data)).hex() if bp else hashlib.sha256(_b(data)).hexdigest()
    return "sha256:" + digest


def merkle_root(leaves: list) -> str:
    """P5 Merkle root via the sealed MerkleTree when present; a deterministic stdlib Merkle otherwise."""
    bp = _bp()
    if bp and leaves:
        return bp.MerkleTree([_b(x) for x in leaves]).get_root().hex()

    def h(s) -> str:
        return hashlib.sha256(_b(s)).hexdigest()

    if not leaves:
        return h("")
    level = [h(x) for x in leaves]
    while len(level) > 1:
        level = [h(level[i] + (level[i + 1] if i + 1 < len(level) else level[i]))
                 for i in range(0, len(level), 2)]
    return level[0]


def new_identity() -> dict | None:
    """A P1 operator identity (secp256k1 keypair). None if the sealed primitives are absent."""
    bp = _bp()
    if not bp:
        return None
    kp = bp.generate_keypair()
    return {"private_key": kp.private_key, "public_key": list(kp.public_key)}


def p1_sign(private_key: int, message: str) -> Optional[dict]:
    """Real P1 ECDSA signature over `message` (the receipt hash). None if primitives absent."""
    bp = _bp()
    if not bp:
        return None
    sig = bp.sign(int(private_key), _b(message))
    return {"r": sig.r, "s": sig.s, "alg": "P1-ECDSA-secp256k1"}


def p1_verify(public_key, message: str, signature: dict) -> bool:
    """Verify a P1 signature (Ch 3 'unmodified since signing' at the cryptographic, not just hash, level)."""
    bp = _bp()
    if not bp or not signature:
        return False
    try:
        sig = bp.ECDSASignature(signature["r"], signature["s"])
        return bool(bp.verify(tuple(public_key), _b(message), sig))
    except Exception:  # noqa: BLE001
        return False
