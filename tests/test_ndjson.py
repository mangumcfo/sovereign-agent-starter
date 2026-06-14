"""Tolerant NDJSON gateway — Universalize Wave §1 (G1 one-home, G2 diagnose-don't-erase).

The single ndjson reader every chain in the tree routes through. These pin the constitutional distinction
(G2): a truncated TRAILING line is quarantined + repairable (survive); a corrupt MIDDLE line is LOUD
(chain_corrupt) and never silently skipped. Plus the owning behavioral fix: repair_chain survives + heals
a truncated tail (it previously raised before repair could run)."""
import json

from sovereign_agent.ndjson import read_ndjson, read_ndjson_cached
from sovereign_agent.obligations import ObligationLedger


def _write(path, lines):
    path.write_text("".join(l if l.endswith("\n") else l + "\n" for l in lines), encoding="utf-8")


def test_missing_and_empty_are_clean(tmp_path):
    miss = read_ndjson(tmp_path / "nope.ndjson")
    assert miss.entries == [] and miss.ok and not miss.chain_corrupt and not miss.repair_required
    empty = tmp_path / "e.ndjson"
    empty.write_text("", encoding="utf-8")
    assert read_ndjson(empty).entries == []


def test_clean_chain_round_trips(tmp_path):
    p = tmp_path / "c.ndjson"
    _write(p, [json.dumps({"n": i}) for i in range(3)])
    r = read_ndjson(p)
    assert [e["n"] for e in r.entries] == [0, 1, 2]
    assert r.ok and not r.chain_corrupt and not r.repair_required


def test_truncated_trailing_line_quarantined_and_survives(tmp_path):
    p = tmp_path / "t.ndjson"
    # two good lines + a truncated final line (interrupted append)
    p.write_text(json.dumps({"n": 0}) + "\n" + json.dumps({"n": 1}) + "\n" + '{"n": 2, "partial', encoding="utf-8")
    r = read_ndjson(p)
    assert [e["n"] for e in r.entries] == [0, 1]      # clean prefix survives
    assert r.ok is True and r.chain_corrupt is False  # a tail is NOT a committed hole
    assert r.repair_required is True and len(r.quarantined) == 1 and r.bad_line is None


def test_corrupt_middle_line_is_loud(tmp_path):
    p = tmp_path / "m.ndjson"
    p.write_text(json.dumps({"n": 0}) + "\n" + '{bad middle}\n' + json.dumps({"n": 2}) + "\n", encoding="utf-8")
    r = read_ndjson(p)
    assert [e["n"] for e in r.entries] == [0, 2]      # parseable entries still returned (to report)
    assert r.chain_corrupt is True and r.ok is False  # but LOUD — a hole, never silent
    assert r.repair_required is True and r.bad_line == 2


def test_cached_reader_rederives_only_on_change(tmp_path):
    p = tmp_path / "k.ndjson"
    _write(p, [json.dumps({"n": 0})])
    first = read_ndjson_cached(p)
    assert read_ndjson_cached(p) is first             # same object → cache hit, no re-parse
    import time
    time.sleep(0.01)
    _write(p, [json.dumps({"n": 0}), json.dumps({"n": 1})])
    second = read_ndjson_cached(p)
    assert second is not first and len(second.entries) == 2


def test_ledger_repair_survives_and_heals_truncated_tail(tmp_path):
    """Owning fix (§1): a ledger whose file ends in a truncated line must still LOAD (clean prefix) and
    repair_chain must drop the dangling tail so the next append cannot turn it into a middle hole."""
    led = ObligationLedger(root=tmp_path)
    led.open("a")
    led.open("b")
    # corrupt the file: append a truncated partial line (an interrupted write)
    with led.path.open("a", encoding="utf-8") as f:
        f.write('{"type": "debit", "trunc')
    led2 = ObligationLedger(root=tmp_path)
    # loads the clean prefix instead of raising
    assert len(led2._entries()) == 2
    res = led2.repair_chain()
    assert res["repaired"] is True                    # the dangling tail forced a heal
    # after repair the file is a clean, verifiable chain with no partial line
    led3 = ObligationLedger(root=tmp_path)
    assert led3.verify_chain() is True
    assert len(led3._entries()) == 2
