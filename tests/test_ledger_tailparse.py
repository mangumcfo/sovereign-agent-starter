"""Append-aware tail parse — audit 2026-06-13c H3/#18.

_entries() now parses only the appended tail on a pure grow (O(Δ) instead of O(n) per write under the
flock), with a head-fingerprint guard that detects a rewrite (repair_chain) and full-re-parses. These
tests prove the tail parse is CORRECT (same result as a cold full parse) and that a rewrite is detected.
"""
from sovereign_agent.obligations import ObligationLedger


def test_tail_parse_matches_cold_full_parse(tmp_path):
    led = ObligationLedger(str(tmp_path), principal_id="node")
    for i in range(20):
        led.open(f"t{i}", classification="C2")
    warm = led._entries()                       # built incrementally via tail parse
    assert len(warm) == 20

    cold = ObligationLedger(str(tmp_path))._entries()   # fresh instance, full parse
    assert [e["id"] for e in warm] == [e["id"] for e in cold]

    for i in range(20, 35):                     # more appends → tail parse extends correctly
        led.open(f"t{i}", classification="C2")
    assert len(led._entries()) == 35
    assert led.verify_chain() is True


def test_rewrite_is_detected_not_trusted_as_append(tmp_path):
    led = ObligationLedger(str(tmp_path), principal_id="node")
    led.open("one", classification="C2")
    led.open("two", classification="C2")
    led._entries()                              # prime the cache (head fingerprint)
    # forge a fork (a hand-written line with a wrong prev_hash) then repair (a full REWRITE/rehash)
    with led.path.open("a") as f:
        f.write('{"type": "debit", "id": "forged", "prev_hash": "genesis", "hash": "deadbeef"}\n')
    assert led.verify_chain() is False
    led.repair_chain()                          # rewrites every line (rehash) → head changes
    assert led.verify_chain() is True
    ids = [e["id"] for e in led._entries()]     # must reflect the rewrite, no stale prefix
    assert "forged" in ids and len(ids) == 3
