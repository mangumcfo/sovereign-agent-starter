"""Fenced JSON store — audit 2026-06-13 W5 #2/#3/#11.

The colocated proposals.json/relays.json stores did unfenced read→mutate→write and lost concurrent
writes. `_jsonstore.update_json` holds an flock across the whole RMW. This proves concurrent cross-PROCESS
appends lose nothing (the same shape as the ledger concurrency test).
"""
import multiprocessing as mp

from sovereign_agent.node_api._jsonstore import read_json, update_json


def _worker(path: str, tag: str, n: int) -> None:
    for i in range(n):
        update_json(path, lambda items: (items + [{"id": f"{tag}-{i}"}], None))


def test_concurrent_cross_process_appends_lose_nothing(tmp_path):
    p = tmp_path / "store.json"
    procs = [mp.Process(target=_worker, args=(str(p), f"P{k}", 30)) for k in range(3)]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join(timeout=60)
    assert all(pr.exitcode == 0 for pr in procs), [pr.exitcode for pr in procs]
    items = read_json(str(p))
    assert len(items) == 90, f"lost writes under concurrency: {len(items)}"
    assert len({it["id"] for it in items}) == 90  # every write survived, none clobbered


def test_update_json_returns_result_and_persists(tmp_path):
    p = tmp_path / "s.json"
    out = update_json(str(p), lambda items: (items + [{"id": "a"}], "added-a"))
    assert out == "added-a"
    assert read_json(str(p)) == [{"id": "a"}]


def test_read_json_tolerates_missing_and_truncated(tmp_path):
    p = tmp_path / "missing.json"
    assert read_json(str(p)) == []
    p.write_text("{ truncated", encoding="utf-8")
    assert read_json(str(p)) == []
