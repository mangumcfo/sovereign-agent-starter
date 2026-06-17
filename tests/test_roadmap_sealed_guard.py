"""roadmap_sealed_guard — the merge rule (f77db98c): sealed/published titles never silently dropped."""
import importlib.util, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rsg", REPO / "scripts" / "roadmap_sealed_guard.py")
rsg = importlib.util.module_from_spec(spec); sys.modules["rsg"] = rsg; spec.loader.exec_module(rsg)


def test_sealed_now_extracts_published_and_sealed():
    rm = {"series": [{"name": "S0", "titles": [
        {"book_id": "a", "title": "A", "stage": "published"},
        {"book_id": "b", "title": "B", "stage": "concept"},
        {"book_id": "c", "title": "C", "stage": "sealed"}]}]}
    got = rsg._sealed_now(rm)
    assert set(got) == {"a", "c"} and "b" not in got


def test_guard_detects_dropped_sealed_title():
    # baseline knows 'a' is sealed; a regen that omits it must be detectable
    full = {"series": [{"name": "S0", "titles": [{"book_id": "a", "title": "A", "stage": "published"}]}]}
    dropped_roadmap = {"series": [{"name": "S0", "titles": []}]}
    base = set(rsg._sealed_now(full))
    present = {b for _, b, _, _ in rsg._titles(dropped_roadmap) if b}
    assert base - present == {"a"}   # the guard's drop set is non-empty → it FAILs


def test_live_roadmap_passes_the_guard():
    # the shipped roadmap + baseline must currently be drop-free (exit 0)
    assert rsg.main() == 0
