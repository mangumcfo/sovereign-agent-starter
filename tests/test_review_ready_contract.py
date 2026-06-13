"""review_ready_contract — the R1 gate deciding whether a book reaches KM's review queue, and
mint_review_packet() opens a real material C1 human-gate obligation. Audit 2026-06-13: a bug flips
review-ready true/false silently — a false-green ships an un-reviewed book. These tests drive evaluate()
against a tmp book dir + tmp ledger, assert each gate flips, and that mint is idempotent.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_ready_contract as rrc  # noqa: E402

_RIGOR = {
    "board": "b", "book_id": "vol_01",
    "findings": [{
        "id": "F1", "severity": "minor", "disposition": "accepted",
        "lgp_alignment": "Strengthens sovereign generational primacy for families across this section.",
        "detail": "A specific, substantive note about the ch1 cross-foot and why it threads to the "
                  "output total — comfortably over eighty characters of genuine review signal.",
    }],
    "section_coverage": [{"section": "ch1", "finding_count": 1}],
}


def _board_md() -> str:
    return f"# Board\n\nprose\n\n```rigor\n{json.dumps(_RIGOR)}\n```\n"


def _brief_md() -> str:
    return ("# Review Brief\n\n"
            "1. Decision: approve the cover direction.\n"
            "2. Judgment call: whether to split chapter 4.\n"
            "3. Decision: choose the epigraph.\n"
            "4. Should we defer the appendix? (decision)\n")


@pytest.fixture
def ready_book(tmp_path, monkeypatch):
    """A book dir + ledger + fidelity wired so ALL four gates pass; returns the bdir."""
    repo = tmp_path / "repo"
    bdir = repo / "book" / "vol_01" / "v1.0"
    (bdir / "final").mkdir(parents=True)
    (repo / "artifacts").mkdir(parents=True)

    # boards
    for rnd in ("round1", "round2", "round3"):
        (bdir / f"editorial_board_review_{rnd}.md").write_text(_board_md(), encoding="utf-8")
    (bdir / "virality_to_ux_translation_v1.md").write_text("present\n", encoding="utf-8")
    (bdir / "tech_arch_review_v1.md").write_text(_board_md(), encoding="utf-8")
    # gate6 renderability: manuscript with a section + a Receipt box
    (bdir / "manuscript_v1.0.md").write_text("# Chapter 1\n\nbody\n\n\U0001F4E6 Receipt Box\n", encoding="utf-8")
    # review brief
    (bdir / "review_brief.md").write_text(_brief_md(), encoding="utf-8")
    # fidelity verdict (PASS) for the book
    gb = repo / "artifacts" / "gb_fidelity.ndjson"
    gb.write_text(json.dumps({"fidelity_verdict": "pass", "book": "vol_01"}) + "\n", encoding="utf-8")

    monkeypatch.setattr(rrc, "REPO", repo)
    monkeypatch.setattr(rrc, "GB_CYLINDER", gb)
    monkeypatch.setattr(rrc, "LEDGER_ROOT", tmp_path / "obligations")
    monkeypatch.setattr(rrc, "_book_dir", lambda book_id: bdir)
    return bdir


def test_all_gates_green_is_review_ready(ready_book):
    res = rrc.evaluate("vol_01", [])
    assert res["review_ready"] is True, res["gaps"]
    assert {c["check"] for c in res["checks"]} == {
        "boards_executed", "obligations_closed", "fidelity_passed", "review_brief_sealed"}


def test_missing_board_flips_to_not_ready(ready_book):
    (ready_book / "editorial_board_review_round3.md").unlink()
    res = rrc.evaluate("vol_01", [])
    assert res["review_ready"] is False
    boards = next(c for c in res["checks"] if c["check"] == "boards_executed")
    assert not boards["pass"] and "editorial_round3" in boards["detail"]


def test_missing_fidelity_flips_to_not_ready(ready_book, monkeypatch):
    # remove ALL fidelity sources: the GB cylinder AND the artifacts/*fidelity*.ndjson REPO.glob finds
    monkeypatch.setattr(rrc, "GB_CYLINDER", ready_book / "nonexistent.ndjson")
    (rrc.REPO / "artifacts" / "gb_fidelity.ndjson").unlink()
    res = rrc.evaluate("vol_01", [])
    assert res["review_ready"] is False
    fid = next(c for c in res["checks"] if c["check"] == "fidelity_passed")
    assert not fid["pass"]


def test_thin_review_brief_flips_to_not_ready(ready_book):
    (ready_book / "review_brief.md").write_text("# Brief\n\n1. Decision: only one call.\n", encoding="utf-8")
    res = rrc.evaluate("vol_01", [])
    assert res["review_ready"] is False
    rb = next(c for c in res["checks"] if c["check"] == "review_brief_sealed")
    assert not rb["pass"]


def test_mint_review_packet_opens_one_and_is_idempotent(ready_book):
    first = rrc.mint_review_packet("vol_01", "Vol 1", [])
    assert first is not None
    second = rrc.mint_review_packet("vol_01", "Vol 1", [])
    assert second == first        # idempotent — no duplicate human-gate packet
    # exactly one review_ready packet exists on the ledger
    from sovereign_agent.obligations.ledger import ObligationLedger
    lg = ObligationLedger(str(rrc.LEDGER_ROOT))
    minted = [o for o in lg.open_obligations() if (o.get("ref") or "") == "review_ready:vol_01"]
    assert len(minted) == 1 and minted[0]["material"] is True
