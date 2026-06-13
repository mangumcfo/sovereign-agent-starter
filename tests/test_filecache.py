"""mtime/size memoization for lens routes — audit 2026-06-13 W5 #4/#5/#15.

Proves a file-derived loader re-derives ONLY when the underlying file changes (the ledger's caching
discipline, propagated to the polled cockpit lenses).
"""
import time as _time

from sovereign_agent.node_api._filecache import memoize_on


def test_memoize_recomputes_only_on_file_change(tmp_path):
    f = tmp_path / "src.txt"
    f.write_text("v1")
    calls = {"n": 0}

    @memoize_on(lambda: [f])
    def load():
        calls["n"] += 1
        return f.read_text()

    assert load() == "v1" and load() == "v1" and load() == "v1"
    assert calls["n"] == 1                      # 3 reads, 1 compute (cache hit on unchanged file)

    _time.sleep(0.01)
    f.write_text("v2")
    assert load() == "v2"
    assert calls["n"] == 2                      # file changed → exactly one re-compute


def test_memoize_handles_missing_file(tmp_path):
    missing = tmp_path / "nope.txt"
    calls = {"n": 0}

    @memoize_on(lambda: [missing])
    def load():
        calls["n"] += 1
        return "default"

    assert load() == "default" and load() == "default"
    assert calls["n"] == 1                      # absent file has a stable (0,0) key → cached
