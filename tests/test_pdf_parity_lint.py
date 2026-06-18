"""Tests for pdf_parity_lint — the rendered-PDF parity checker.

Verifies the calibration discipline (PASS the S2 pen, never exceed it) and that the three checks behave:
font-set, reader-artifacts, source-glyphs. Uses synthetic inputs so the suite has no PDF dependency for the
pure-logic checks; the font check is exercised via the family-classification helper.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pdf_parity_lint as p


def test_font_family_strips_subset_prefix():
    assert p._font_family("VTXKUP+Noto-Serif-Bold") == "Noto-Serif-Bold"
    assert p._font_family("DejaVu-Serif-Bold") == "DejaVu-Serif-Bold"


def test_approved_roots_accept_s2_set_reject_stray():
    crit = p._DEFAULT
    roots = crit["approved_font_roots"]
    s2_like = ["Noto-Serif", "Noto-Serif-Bold", "Liberation-Serif", "Liberation-Mono-Bold"]
    assert all(any(f.startswith(r) for r in roots) for f in s2_like)         # S2 pen passes
    for stray in ("DejaVu-Serif-Bold", "Noto-Color-Emoji"):
        assert not any(stray.startswith(r) for r in roots)                   # stray families flagged


def test_seal_glyph_not_banned_passes_s2():
    # ∞Δ∞ is intentional in the published S2 pen; a check must PASS S2, never exceed it.
    import re
    pats = p._DEFAULT["banned_reader_artifacts"]
    assert not any(re.search(pat, "section close ∞Δ∞") for pat in pats)


def test_raw_bold_and_fence_are_banned():
    import re
    pats = p._DEFAULT["banned_reader_artifacts"]
    assert any(re.search(pat, "Specialization Signal:** leaked") for pat in pats)   # the :**** defect tail
    assert any(re.search(pat, "```") for pat in pats)                                # raw code fence


def test_box_glyph_is_a_fallback_offender():
    assert "▣" in p._DEFAULT["banned_source_glyphs"]   # ▣ forces the DejaVu fallback


def test_source_glyph_check_flags_box_icon(tmp_path):
    md = tmp_path / "manuscript_v1.0.md"
    md.write_text("> **▣ RECEIPT — Ch 1**\nbody\n", encoding="utf-8")
    res = p.check_source_glyphs(str(md), p._DEFAULT)
    assert not res["pass"] and "U+25A3" in res["found"]
    md.write_text("> **RECEIPT — Ch 1**\nbody\n", encoding="utf-8")     # glyph removed (the v1.8 fix)
    assert p.check_source_glyphs(str(md), p._DEFAULT)["pass"]
