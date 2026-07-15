"""Crypto vector assurance in the test suite — runs on every commit (Lane 1, deterministic).
The sealed P1/P5 primitives must pass NIST/secp256k1 known-answer vectors AND cross-verify against the
`cryptography` reference lib. A red here = substrate-correctness failure (the books' verifiability claim)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import crypto_vector_check as V


def test_crypto_vectors_all_green():
    res = V.run()
    failed = [c["name"] for c in res["checks"] if not c["pass"]]
    assert res["pass"], f"crypto vector check RED: {failed}"
    assert res["n_total"] >= 10, "vector suite suspiciously small"


def test_p1_cryptography_interop_present():
    res = V.run()
    names = {c["name"]: c["pass"] for c in res["checks"]}
    assert names.get("interop_p1sig_verifies_in_cryptography"), "P1 sig must verify under cryptography"
    assert names.get("interop_cryptographysig_verifies_in_p1"), "cryptography sig must verify under P1"
