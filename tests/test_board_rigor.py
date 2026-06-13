"""board_rigor — the "no rubber stamps" gate wired into review_ready_contract._check_boards.
Audit 2026-06-13: a too-lax regex/threshold is exactly what this gate exists to prevent, with nothing
to catch it. Tests: a clean board passes; one violation per rule fails its rule; rigor_check_md handles
valid / missing-block / invalid-JSON.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import board_rigor as br  # noqa: E402


def _good_finding(**over):
    f = {
        "id": "F1", "severity": "minor", "disposition": "accepted",
        "lgp_alignment": "Strengthens sovereign generational primacy for families across this section.",
        "detail": "A specific, substantive observation about the cross-foot on the assumptions sheet "
                  "and why it threads to the output total — well over eighty characters of real signal.",
    }
    f.update(over)
    return f


def _good_board(**over):
    d = {"board": "editorial_r1", "book_id": "vol_01",
         "findings": [_good_finding()],
         "section_coverage": [{"section": "ch1", "finding_count": 1}]}
    d.update(over)
    return d


def test_clean_board_passes():
    r = br.rigor_check(_good_board())
    assert r["pass"], r["gaps"]
    assert all(not g for g in r["rules"].values())


def test_r_lgp_violation():
    r = br.rigor_check(_good_board(findings=[_good_finding(lgp_alignment="short")]))
    assert not r["pass"] and r["rules"]["R-LGP"]


def test_r_obl_violation():
    r = br.rigor_check(_good_board(findings=[_good_finding(severity="material", obligation_id="")]))
    assert not r["pass"] and r["rules"]["R-OBL"]


def test_r_depth_violation():
    r = br.rigor_check(_good_board(section_coverage=[{"section": "ch1", "finding_count": 0}]))
    assert not r["pass"] and r["rules"]["R-DEPTH"]


def test_r_human_violation_boilerplate():
    r = br.rigor_check(_good_board(findings=[_good_finding(detail="looks good")]))
    assert not r["pass"] and r["rules"]["R-HUMAN"]


def test_r_struct_empty_board():
    r = br.rigor_check({"board": "x", "book_id": "y", "findings": [], "section_coverage": []})
    assert not r["pass"] and r["rules"]["R-STRUCT"]


# ── rigor_check_md ──────────────────────────────────────────────────────────────────────────────
def _wrap(json_text: str) -> str:
    return f"# Board\n\nsome prose\n\n```rigor\n{json_text}\n```\n\nmore prose\n"


def test_md_valid_block_passes():
    import json
    r = br.rigor_check_md(_wrap(json.dumps(_good_board())))
    assert r["pass"], r["gaps"]


def test_md_missing_block_fails_structural():
    r = br.rigor_check_md("# Board\n\nno embedded machine block here\n")
    assert not r["pass"] and any("no embedded" in g for g in r["gaps"])


def test_md_invalid_json_fails():
    r = br.rigor_check_md(_wrap("{ not: valid json, }"))
    assert not r["pass"] and any("invalid JSON" in g for g in r["gaps"])
