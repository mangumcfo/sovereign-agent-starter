"""/goal Scout packet-lint — the anti-slop gate (spec GB_goal_Scout_Synthesis_2026-06-15.md §3/§4).

Proves the lint mechanically REJECTS slop, that earned-Green requires the evidence to RESOLVE (the
confident-but-wrong catch — GB's kill-line condition), and that a clean packet passes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scout_lint as L  # noqa: E402


def _clean_packet():
    ref = "artifacts/book_code_tree.json#unrendered_chapters"  # a ref that RESOLVES in-repo
    return {
        "title_id": "01_cfos_finance", "status": "yellow",
        "top_next_tasks": [{"task": "Review unrendered chapters", "evidence_ref": ref, "effort": "S"}],
        "evidence_refs": [ref],
        "confidence": "Deterministic deriver over book_code_tree.json findings (12 ids).",
    }


def test_clean_packet_passes():
    ok, rejects = L.lint_packet(_clean_packet())
    assert ok, rejects


def test_rejects_no_evidence_refs():
    p = _clean_packet(); p["evidence_refs"] = []
    ok, rejects = L.lint_packet(p)
    assert not ok and any("evidence_refs" in r for r in rejects)


def test_rejects_too_many_tasks():
    p = _clean_packet()
    p["top_next_tasks"] = [{"task": f"t{i}", "evidence_ref": "scripts/scout_lint.py"} for i in range(6)]
    ok, rejects = L.lint_packet(p)
    assert not ok and any("tasks" in r for r in rejects)


def test_rejects_task_without_evidence():
    p = _clean_packet(); p["top_next_tasks"] = [{"task": "do a thing"}]  # no evidence_ref → can't state why
    ok, rejects = L.lint_packet(p)
    assert not ok and any("evidence_ref" in r for r in rejects)


def test_rejects_bare_confidence():
    p = _clean_packet(); p["confidence"] = "high"
    ok, rejects = L.lint_packet(p)
    assert not ok and any("confidence" in r for r in rejects)


def test_rejects_prose_out_of_fit_gate():
    p = _clean_packet(); p["note"] = "Here is a draft of the chapter prose to author for the reader."
    ok, rejects = L.lint_packet(p)
    assert not ok and any("fit-gate" in r or "prose" in r for r in rejects)


# ── earned-Green item-level: the RESOLVE check (confident-but-wrong) ─────────────────────────────
def test_item_green_requires_resolving_evidence():
    good = {"evidence_ref": "scripts/scout_lint.py", "location": "L1", "reason": "x dead",
            "action": "remove", "confidence": "ruff F401 flagged it; the import is unused at module scope."}
    assert L.lint_item(good)[0] == "GREEN"


def test_item_confident_but_wrong_is_not_green():
    """A fully-formed item whose evidence_ref does NOT resolve cannot be Green — the kill-line guard."""
    bad = {"evidence_ref": "src/does_not_exist.py:99", "location": "L99", "reason": "x dead",
           "action": "remove", "confidence": "looks unused to me, fairly sure about this one."}
    verdict, reasons = L.lint_item(bad)
    assert verdict != "GREEN" and any("resolve" in r for r in reasons)


def test_item_out_of_fit_is_red():
    v, _ = L.lint_item({"item": "rewrite the architecture", "evidence_ref": "scripts/scout_lint.py",
                        "reason": "r", "action": "redesign", "confidence": "basis here for sure"})
    assert v == "RED"
