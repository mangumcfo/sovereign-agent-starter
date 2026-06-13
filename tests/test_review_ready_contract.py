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


def _open_obl(root, **kw):
    from sovereign_agent.obligations.ledger import ObligationLedger
    return ObligationLedger(str(root), principal_id="KM-1176").open(**kw)


def test_check_obligations_flips_red_on_open_blocking(ready_book):
    """H5: an OPEN, non-deferred obligation for the book must BLOCK review-ready (the gate never flipped
    red in any test before — a regression in _matches/_deferred could ship a false-green book)."""
    _open_obl(rrc.LEDGER_ROOT, title="vol_01 cross-foot fix", intent="open work on vol_01", ref="vol_01")
    res = rrc.evaluate("vol_01", [])
    assert res["review_ready"] is False
    oc = next(c for c in res["checks"] if c["check"] == "obligations_closed")
    assert not oc["pass"] and oc["blocking_ids"]


def test_check_obligations_deferred_does_not_block(ready_book):
    """A 'defer'-tagged open obligation does NOT block (covers _deferred)."""
    _open_obl(rrc.LEDGER_ROOT, title="vol_01 later", intent="defer this vol_01 item to v1.1", ref="vol_01")
    res = rrc.evaluate("vol_01", [])
    oc = next(c for c in res["checks"] if c["check"] == "obligations_closed")
    assert oc["pass"], oc          # deferred → not blocking


def test_check_obligations_review_packet_self_excluded(ready_book):
    """The review_ready:<book> human-gate packet must NOT count against the book's own readiness
    (covers the line-176 self-exclusion)."""
    _open_obl(rrc.LEDGER_ROOT, title="sign off vol_01", intent="review", ref="review_ready:vol_01")
    res = rrc.evaluate("vol_01", [])
    oc = next(c for c in res["checks"] if c["check"] == "obligations_closed")
    assert oc["pass"], oc


def test_gate6_renderability_red_paths(ready_book):
    """#19: Gate-6 (Receipt-box anchor) red paths — zero boxes and a partial (box-less 2nd section)."""
    ms = ready_book / "manuscript_v1.0.md"
    ms.write_text("# Chapter 1\n\nbody, no receipt box\n", encoding="utf-8")          # zero boxes
    g6 = rrc._check_gate6_renderability(ready_book)
    assert g6["status"] == "no-receipt-boxes" and not g6["pass"]
    ms.write_text("# Chapter 1\n\n\U0001F4E6 Receipt Box\n\n# Chapter 2\n\nno box here\n", encoding="utf-8")
    g6 = rrc._check_gate6_renderability(ready_book)
    assert g6["status"].startswith("partial") and not g6["pass"]


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
