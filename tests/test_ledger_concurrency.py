"""Concurrency / write-fence tests for the ObligationLedger (audit 2026-06-10 CRITICAL).

The audit reproduced the fork empirically: 8 threads x 25 open() calls produced 100 duplicate
prev_hash entries and verify_chain()==False; two instances on one shared root also corrupted the chain.
These tests are the green evidence for the fcntl.flock fix in _append + the repair_chain() command.
"""
import threading

from sovereign_agent.obligations import ObligationLedger


def _prev_hashes(led):
    return [e["prev_hash"] for e in led._entries()]


def test_in_process_threads_do_not_fork_the_chain(tmp_path):
    """8 threads x 25 opens against ONE singleton ledger — the threaded=True in-process race."""
    led = ObligationLedger(str(tmp_path), principal_id="node")
    errors = []

    def hammer(t):
        try:
            for i in range(25):
                led.open(title=f"t{t}-{i}", classification="C2")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=hammer, args=(t,)) for t in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert not errors, f"appenders raised: {errors}"
    entries = led._entries()
    assert len(entries) == 200, f"lost/duplicated writes: {len(entries)}"
    # No two entries may share a prev_hash (that IS the fork signature).
    ph = _prev_hashes(led)
    assert len(ph) == len(set(ph)), "duplicate prev_hash → the chain forked"
    assert led.verify_chain() is True, "chain broke under concurrent in-process appends"


def test_two_instances_on_one_root_do_not_fork(tmp_path):
    """Two distinct ObligationLedger objects on the SAME root — the cross-process race
    (review_ready_contract.py + the live API appending to atrium_review at once)."""
    a = ObligationLedger(str(tmp_path), principal_id="node")
    b = ObligationLedger(str(tmp_path), principal_id="node")
    errors = []

    def hammer(led, tag):
        try:
            for i in range(40):
                led.open(title=f"{tag}-{i}", classification="C2")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=hammer, args=(a, "A"))
    t2 = threading.Thread(target=hammer, args=(b, "B"))
    t1.start(); t2.start(); t1.join(); t2.join()

    assert not errors, f"appenders raised: {errors}"
    assert len(a._entries()) == 80
    ph = _prev_hashes(a)
    assert len(ph) == len(set(ph)), "duplicate prev_hash across two instances → fork"
    assert a.verify_chain() is True


def test_repair_chain_relinks_a_forked_ledger(tmp_path):
    """repair_chain() makes an already-forked ledger verify again, backing up the raw fork."""
    led = ObligationLedger(str(tmp_path), principal_id="node")
    led.open(title="one", classification="C2")
    led.open(title="two", classification="C2")
    # Forge a fork: append a hand-written line with a wrong prev_hash.
    with led.path.open("a") as f:
        f.write('{"type": "debit", "id": "forged", "prev_hash": "genesis", "hash": "deadbeef"}\n')
    assert led.verify_chain() is False

    res = led.repair_chain()
    assert res["repaired"] is True
    assert res["was_valid"] is False
    assert res["backup"] is not None
    assert led.verify_chain() is True, "repair_chain did not restore a valid chain"

    # Idempotent: a second repair on a now-valid chain is a no-op.
    res2 = led.repair_chain()
    assert res2["repaired"] is False and res2["was_valid"] is True
