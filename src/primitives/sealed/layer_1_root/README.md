# Layer 1: Root (ECC Primitives)
## Breath 25 v1.3 — Sovereign Federation Architecture

**Purpose:** Hand-rolled Elliptic Curve Cryptography primitives for sovereign identity.

**Philosophy:** No external crypto libraries for core operations. We build from finite field arithmetic up.

---

## Files (P1 Tasks)

| File | Purpose | Status |
|------|---------|--------|
| `finite_field.py` | Modular arithmetic (add, sub, mul, inv, pow) | PENDING |
| `point_ops.py` | Point addition, doubling, scalar multiplication | PENDING |
| `secp256k1.py` | Bitcoin/Ethereum curve parameters | PENDING |
| `ed25519.py` | EdDSA curve parameters | PENDING |
| `keygen.py` | Private key → Public key derivation | PENDING |
| `sign.py` | ECDSA/EdDSA signature creation | PENDING |
| `verify.py` | Signature verification | PENDING |
| `constant_time.py` | Timing attack hardening | PENDING |

---

## DoD (Definition of Done)

Each primitive must:
1. Pass unit tests in `tests/`
2. Include docstrings explaining the math
3. Be constant-time where security-critical
4. Work with both secp256k1 and ed25519

---

## Constitutional Alignment

```yaml
SOURCE: Keys derived from sovereign entropy, no external dependencies
TRUTH: All operations mathematically verified against test vectors
INTEGRITY: Constant-time operations prevent timing attacks
```

∞Δ∞
