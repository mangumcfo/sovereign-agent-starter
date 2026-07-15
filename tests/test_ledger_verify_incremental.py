"""Incremental verify_chain (scaling_receipted_engine, audit 2026-06-11).

verify_chain is recomputed on every GET /obligations (chain_ok) — O(n) re-hash per read does not scale.
It is now memoized on the file-identity key and advanced in-lock on append. These tests assert BOTH:
  · correctness is unchanged — valid→True, tamper→False, repair→True;
  · the fast paths do zero re-hashing — unchanged-file re-verify and append-then-verify are O(1).
"""
import json
import unittest.mock as mock

import sovereign_agent.obligations.ledger as L


def _count_hash(monkey_target=L):
    """A counting wrapper around the module-level _hash, returning (patcher, counter)."""
    real = L._hash
    calls = {"n": 0}

    def counting(obj):
        calls["n"] += 1
        return real(obj)

    return mock.patch.object(monkey_target, "_hash", counting), calls


def test_verify_correctness_preserved(tmp_path):
    led = L.ObligationLedger(root=tmp_path)
    for i in range(5):
        led.open(f"obligation {i}")
    assert led.verify_chain() is True
    led.open("obligation 5")
    assert led.verify_chain() is True   # still valid after more appends

    # tamper an early entry on disk (changes its length → file identity bumps) → caught
    lines = led.path.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["title"] = "TAMPERED — content no longer matches its stored hash"
    lines[1] = json.dumps(rec, sort_keys=True)
    led.path.write_text("\n".join(lines) + "\n")
    led._entries_cache = None            # force a fresh parse (mirrors a new process reading the file)
    assert led.verify_chain() is False   # memoization did NOT hide the tamper (file identity changed)

    # repair re-links and verify is True again
    assert led.repair_chain()["repaired"] is True
    assert led.verify_chain() is True


def test_unchanged_file_reverify_is_o1(tmp_path):
    led = L.ObligationLedger(root=tmp_path)
    for i in range(6):
        led.open(f"o{i}")
    assert led.verify_chain() is True    # full walk, caches the verdict

    patcher, calls = _count_hash()
    with patcher:
        for _ in range(10):
            assert led.verify_chain() is True
    assert calls["n"] == 0               # 10 re-verifies on an unchanged file → zero re-hashing


def test_append_then_verify_is_o1(tmp_path):
    led = L.ObligationLedger(root=tmp_path)
    for i in range(6):
        led.open(f"o{i}")
    assert led.verify_chain() is True    # frontier is now known-valid

    patcher, calls = _count_hash()
    with patcher:
        led.open("o6")                   # _append hashes exactly the ONE new entry...
        after_append = calls["n"]
        assert led.verify_chain() is True
        after_verify = calls["n"]
    assert after_append == 1             # only the new entry was hashed by the append
    assert after_verify == after_append  # verify added ZERO hashes — frontier advanced incrementally


def test_full_verify_after_unknown_state_recomputes(tmp_path):
    # A fresh ledger instance pointed at an existing chain has no warm cache → first verify is a full,
    # correct recompute (no false-positive from an empty cache).
    led = L.ObligationLedger(root=tmp_path)
    for i in range(4):
        led.open(f"o{i}")
    fresh = L.ObligationLedger(root=tmp_path)
    assert fresh.verify_chain() is True
