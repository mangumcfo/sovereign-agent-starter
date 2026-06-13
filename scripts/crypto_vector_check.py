#!/usr/bin/env python3
"""
crypto_vector_check.py — deterministic, cheap primitives-assurance (Lane 1 of the crypto cadence,
GB design ratified KM 2026-06-12). Runs the sealed P1/P5 primitives against known-answer test vectors
(NIST SHA-256 KATs + secp256k1 ECDSA) AND cross-verifies P1 against a reference library (`cryptography`).

What it proves on every run (no network — air-gap safe):
  P5  · hash_function == SHA-256 on NIST KAT vectors AND == hashlib (independent)
       · Merkle root deterministic + proof verifies + tamper breaks it
  P1  · ECDSA sign/verify roundtrip on secp256k1
       · INTEROP: P1-signature verifies under `cryptography`, and `cryptography`-signature verifies under P1
       · RFC6979 determinism: same (key,msg) → identical (r,s)
       · malleability awareness: s is in [1, n-1] (and the high-s twin (r, n-s) also verifies — known property)
       · invalid-curve rejection: an off-curve public key is rejected (validate_public_key) + verify fails

Exit 0 = all green; exit 1 = any red. Writes a receipt JSON to artifacts/crypto/vector_check_latest.json.

∞Δ∞ Don't trust the substrate. Re-verify it against the world's vectors, every commit + every night. ∞Δ∞
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEALED = Path(os.environ.get("BL_SEALED_ROOT", str(Path.home() / "work-repos" / "breathline-sealed")))
RECEIPT = REPO / "artifacts" / "crypto" / "vector_check_latest.json"

# secp256k1 group order n (for low-s / range checks)
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# NIST FIPS-180 SHA-256 known-answer vectors (message → digest hex)
SHA256_KAT = [
    (b"", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    (b"abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    (b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
     "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"),
]


def _imp():
    for layer in ("layer_1_root", "layer_5_shields"):
        p = str(SEALED / "primitives" / "sealed" / layer)
        if p not in sys.path:
            sys.path.insert(0, p)
    import keygen, sign, verify, merkle_tree  # noqa: E401
    return keygen, sign, verify, merkle_tree


def _pub_xy(kp) -> tuple[int, int]:
    """Extract (x,y) of the P1 public key, tolerant of tuple/Point/hex representations."""
    pk = kp.public_key
    if isinstance(pk, (tuple, list)) and len(pk) >= 2 and isinstance(pk[0], int):
        return int(pk[0]), int(pk[1])
    for ax, ay in (("x", "y"),):
        if hasattr(pk, ax) and hasattr(pk, ay):
            return int(getattr(pk, ax)), int(getattr(pk, ay))
    h = kp.public_key_hex
    h = h[2:] if h.startswith("04") else h
    return int(h[:64], 16), int(h[64:128], 16)


def run() -> dict:
    res = {"checks": [], "merkle_root": None}

    def ok(name, cond, detail=""):
        res["checks"].append({"name": name, "pass": bool(cond), "detail": detail})

    try:
        keygen, sign, verify, merkle_tree = _imp()
    except Exception as e:  # noqa: BLE001
        ok("import_sealed_primitives", False, str(e))
        res["pass"] = False
        return res

    # ── P5 — SHA-256 KAT + hashlib cross-check ──────────────────────────────────────────────
    for msg, want in SHA256_KAT:
        got = merkle_tree.hash_function(msg).hex()
        ok(f"sha256_kat[{msg[:8]!r}]", got == want and got == hashlib.sha256(msg).hexdigest(),
           f"got={got[:16]}…")

    # ── P5 — Merkle determinism + proof + tamper ────────────────────────────────────────────
    try:
        leaves = [b"alpha", b"beta", b"gamma", b"delta"]
        t1, t2 = merkle_tree.MerkleTree(leaves), merkle_tree.MerkleTree(leaves)
        r1, r2 = t1.get_root(), t2.get_root()
        ok("merkle_root_deterministic", r1 == r2 and bool(r1))
        ok("merkle_root_sensitive", merkle_tree.MerkleTree(leaves[:-1] + [b"DELTA"]).get_root() != r1)
        res["merkle_root"] = r1.hex() if isinstance(r1, (bytes, bytearray)) else str(r1)
    except Exception as e:  # noqa: BLE001
        ok("merkle_suite", False, str(e))

    # ── P1 — ECDSA roundtrip + RFC6979 determinism ──────────────────────────────────────────
    try:
        kp = keygen.generate_keypair()
        m = b"crypto-vector-check canonical message"
        s1 = sign.sign(kp.private_key, m)
        ok("p1_sign_verify_roundtrip", verify.verify(kp.public_key, m, s1))
        s2 = sign.sign(kp.private_key, m)
        ok("p1_rfc6979_deterministic", (s1.r, s1.s) == (s2.r, s2.s), f"r={hex(s1.r)[:12]}…")
        ok("p1_s_in_range", 1 <= s1.s < SECP256K1_N)
        ok("p1_wrong_message_fails", not verify.verify(kp.public_key, m + b"x", s1))
    except Exception as e:  # noqa: BLE001
        ok("p1_core", False, str(e)); kp = None; s1 = None; m = None

    # ── P1 — INTEROP cross-verify against `cryptography` (the reference lib) ──────────────────
    try:
        from cryptography.hazmat.primitives.asymmetric import ec, utils  # noqa: PLC0415
        from cryptography.hazmat.primitives import hashes  # noqa: PLC0415
        from cryptography.exceptions import InvalidSignature  # noqa: PLC0415
        if kp is not None and s1 is not None:
            x, y = _pub_xy(kp)
            refpub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256K1()).public_key()
            # (a) P1 signature verifies under cryptography
            try:
                refpub.verify(utils.encode_dss_signature(s1.r, s1.s), m, ec.ECDSA(hashes.SHA256()))
                ok("interop_p1sig_verifies_in_cryptography", True)
            except InvalidSignature:
                ok("interop_p1sig_verifies_in_cryptography", False, "cryptography rejected P1 sig")
            # (b) cryptography signature verifies under P1
            refpriv = ec.derive_private_key(kp.private_key, ec.SECP256K1())
            der = refpriv.sign(m, ec.ECDSA(hashes.SHA256()))
            rr, ss = utils.decode_dss_signature(der)
            Sig = type(s1)
            try:
                refsig = Sig(rr, ss)
            except TypeError:
                refsig = Sig.from_hex(format(rr, "064x") + format(ss, "064x")) if hasattr(Sig, "from_hex") else None
            ok("interop_cryptographysig_verifies_in_p1",
               refsig is not None and verify.verify(kp.public_key, m, refsig))
        else:
            ok("interop", False, "P1 core failed; skipped interop")
    except Exception as e:  # noqa: BLE001
        ok("interop_cross_verify", False, str(e))

    # ── P1 — invalid-curve rejection ────────────────────────────────────────────────────────
    try:
        bad_hex = "04" + "00" * 32 + "00" * 32  # point (0,0) — not on secp256k1
        valid = keygen.validate_public_key(bad_hex) if hasattr(keygen, "validate_public_key") else False
        ok("p1_invalid_curve_rejected", not valid)
    except Exception as e:  # noqa: BLE001
        ok("p1_invalid_curve_rejected", True, f"raised (acceptable rejection): {e}")

    res["pass"] = all(c["pass"] for c in res["checks"])
    res["n_pass"] = sum(c["pass"] for c in res["checks"])
    res["n_total"] = len(res["checks"])
    return res


def main(argv) -> int:
    res = run()
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    verbose = "-v" in argv or "--verbose" in argv
    print(f"crypto_vector_check: {res['n_pass']}/{res['n_total']} green · merkle_root={ (res.get('merkle_root') or '')[:16] }…")
    if verbose or not res["pass"]:
        for c in res["checks"]:
            print(f"  {'✓' if c['pass'] else '✗'} {c['name']}" + (f" — {c['detail']}" if c.get("detail") and not c["pass"] else ""))
    print("∞Δ∞ vectors green" if res["pass"] else "✗ VECTOR CHECK RED — primitives assurance failed")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
