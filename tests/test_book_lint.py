"""Tests for book_lint — the S2-pen production-standards checker."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import book_lint as b

_GOOD_TOC = """## Table of Contents

- Preflight: Verify Before You Read Chapter 1
- Executive Brief
- Chapter 1: The First Thing
- Chapter 2: The Second Thing
- About the Author

\\newpage
"""

_GOOD_BODY = """# Chapter 1: The First Thing

Prose.

## Industry Signal

> signal text

## Your Next Steps

1. do it

> **RECEIPT — Ch 1 · sealed**
> claim

# Chapter 2: The Second Thing

More prose.

## Industry Signal

> s

## Your Next Steps

1. go

> **RECEIPT — Ch 2 · sealed**
> claim
"""


def _write(tmp_path, text):
    p = tmp_path / "manuscript_v1.0.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_clean_manuscript_passes(tmp_path):
    r = b.lint(_write(tmp_path, _GOOD_TOC + _GOOD_BODY))
    assert r["pass"], [c for c in r["checks"] if not c["pass"]]


def test_banned_artifacts_flagged(tmp_path):
    md = _GOOD_TOC + _GOOD_BODY + "\n(eBook edition: no ISBN required)\n\n---\n"
    r = b.lint(_write(tmp_path, md))
    c = next(c for c in r["checks"] if c["check"] == "banned_artifacts")
    assert not c["pass"]


def test_numbered_grouped_toc_flagged(tmp_path):
    bad_toc = "## Table of Contents\n\n**Chapters**\n\n1. The First Thing\n2. The Second Thing\n\n\\newpage\n"
    r = b.lint(_write(tmp_path, bad_toc + _GOOD_BODY))
    c = next(c for c in r["checks"] if c["check"] == "toc_format")
    assert not c["pass"]


def test_receipt_mid_chapter_flagged(tmp_path):
    mid = """# Chapter 1: X

> **RECEIPT — Ch 1 · early**
> claim

## Industry Signal

> s

## Your Next Steps

1. go
"""
    r = b.lint(_write(tmp_path, _GOOD_TOC + mid))
    c = next(c for c in r["checks"] if c["check"] == "chapter_end_order")
    assert not c["pass"] and "receipt-mid-chapter" in c["detail"]


def test_clumped_labels_flagged(tmp_path):
    clump = _GOOD_TOC + _GOOD_BODY + "\n# Connect\n\n**Website:** a\n**Email:** b\n**LinkedIn:** c\n"
    r = b.lint(_write(tmp_path, clump))
    c = next(c for c in r["checks"] if c["check"] == "callout_clumping")
    assert not c["pass"]


def test_adjacent_figures_flagged(tmp_path):
    figs = _GOOD_TOC + _GOOD_BODY + "\n[VISUAL: Figure 1.1 -- a -- see images]\n[VISUAL: Figure 1.2 -- b -- see images]\n"
    r = b.lint(_write(tmp_path, figs))
    c = next(c for c in r["checks"] if c["check"] == "figure_placement")
    assert not c["pass"]
