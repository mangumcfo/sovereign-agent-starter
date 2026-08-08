# -*- coding: utf-8 -*-
"""Proof-first tests for sovereign_ux.render_covenant (S8 Vol 8, the capstone).

Kill-targets pinned: renders-never-rewrites (read-only) · no-second-authority (imports only the Lens) ·
drift-checked/living (verify_covenant detects any change) · inspectable (any article read-only, unknown
denies) · weakest-party verifiable (a green light on ONE article proves the WHOLE covenant unaltered).
"""
import copy
import pathlib

import pytest

from sovereign_agent.sovereign_ux.render_covenant import (
    render_covenant,
    inspect_article,
    verify_covenant,
)


COVENANT = {
    "article_1_primacy": "The human ratifier is the source of authority; no node overrides the seal.",
    "article_2_breath": "Every material act passes a breath-gate held by a human.",
    "article_3_receipts": "Every act leaves a hash-chained receipt any successor can replay.",
    "article_4_succession": "A node renders the same records at every level so an heir can inherit it.",
}
MANDATE = "successor-read"


def test_renders_the_whole_covenant():
    v = render_covenant(COVENANT, mandate=MANDATE)
    assert v.object_type == "dict"
    # every article is present in a full render (fields=None → all fields)
    for art in COVENANT:
        assert art in v.content
    assert v.mandate == MANDATE


def test_inspect_one_article_reads_only_that_article():
    v = inspect_article(COVENANT, "article_2_breath", mandate=MANDATE)
    assert "article_2_breath" in v.content
    # the other articles are omitted from THIS view (inspect one)
    assert "article_1_primacy" not in v.content
    assert "article_3_receipts" not in v.content


def test_inspect_unknown_article_shows_nothing():
    # deny-by-default: a mis-named article projects an empty view, never the whole covenant
    v = inspect_article(COVENANT, "article_99_forgery", mandate=MANDATE)
    assert not v.content
    assert "article_1_primacy" not in v.content


def test_rendering_is_read_only():
    before = copy.deepcopy(COVENANT)
    v = render_covenant(COVENANT, mandate=MANDATE)
    # mutating the rendered view's content must not reach the source covenant
    try:
        v.content["article_1_primacy"] = "TAMPERED"
    except (TypeError, AttributeError):
        pass  # frozen/immutable content is even stronger — still read-only
    assert COVENANT == before, "render_covenant must never mutate the covenant"


def test_article_view_fingerprints_the_whole_covenant():
    # weakest-party spine: an article view and the full render share ONE fingerprint of the WHOLE covenant
    whole = render_covenant(COVENANT, mandate=MANDATE)
    one = inspect_article(COVENANT, "article_2_breath", mandate=MANDATE)
    assert one.fingerprint == whole.fingerprint


def test_verify_covenant_fresh_when_unchanged():
    v = inspect_article(COVENANT, "article_2_breath", mandate=MANDATE)
    st = verify_covenant(v, COVENANT)
    assert st.fresh is True
    assert st.drift is False


def test_verify_covenant_detects_a_change_the_reader_never_saw():
    # an heir inspects ONE article; a change to a DIFFERENT article still flips the green light to drift
    v = inspect_article(COVENANT, "article_2_breath", mandate=MANDATE)
    tampered = dict(COVENANT)
    tampered["article_1_primacy"] = "A node may override the seal."  # a change elsewhere
    st = verify_covenant(v, tampered)
    assert st.fresh is False
    assert st.drift is True


def test_verify_covenant_detects_a_change_in_the_inspected_article():
    v = inspect_article(COVENANT, "article_3_receipts", mandate=MANDATE)
    tampered = dict(COVENANT)
    tampered["article_3_receipts"] = "Receipts are optional."
    st = verify_covenant(v, tampered)
    assert st.drift is True


def test_imports_only_the_lens_no_second_authority():
    # no-second-authority: render_covenant composes ONLY the Lens — it authors/enforces/amends nothing.
    # Scan IMPORT LINES + CODE (docstring prose legitimately names the composed sealed floors).
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "sovereign_ux" / "render_covenant.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    forbidden = ("breath_gate", "constitutions", "verify_surface", "seal", "hmac", "ecdsa", "hashlib")
    for ln in import_lines:
        for tok in forbidden:
            assert tok not in ln.lower(), f"render_covenant must not import {tok} — compose the sealed floor, roll nothing"
    # composes the Lens by identity — its ONLY intra-package import
    lens_imports = [ln for ln in import_lines if "from ." in ln]
    assert lens_imports == ["from .lens import render_view, verify_view, View, ViewStatus    # V01 The Sovereign Lens"], \
        "render_covenant's only sibling import must be the Sovereign Lens"
