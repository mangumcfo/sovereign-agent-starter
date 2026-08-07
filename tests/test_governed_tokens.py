# -*- coding: utf-8 -*-
"""Acceptance tests for The Governed Aesthetic (S8 Vol 3) — tokens.

Proves: a governed token set is the owner's frozen object · apply_tokens resolves governed token
references to their values and REFUSES an off-token render (deny-by-default) · validate_drift reports
off-token references without rendering · apply_tokens composes the Sovereign Lens (Vol 1) only ·
content-agnostic. No aesthetic claim. Crypto-free.
"""
import dataclasses
import pytest

from sovereign_agent.sovereign_ux.tokens import (
    TokenSet, TokenDrift, apply_tokens, validate_drift,
)

_TOKENS = TokenSet(name="ridgeline.brand", tokens={
    "brand.primary": "#0B2A4A",
    "brand.gold": "#C7A24B",
    "space.md": 16,
    "type.body": "Arial 11pt",
})


# ---- the token set is the owner's governed object --------------------------------------------

def test_token_set_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _TOKENS.name = "hijacked"  # type: ignore[misc]


def test_resolve_governed_and_refuse_off_token():
    assert _TOKENS.resolve("brand.primary") == "#0B2A4A"
    with pytest.raises(TokenDrift):
        _TOKENS.resolve("brand.NEON")  # off-token, deny-by-default


# ---- validate_drift: report off-token references without rendering ---------------------------

def test_validate_drift_clean_when_all_governed():
    obj = {"header": {"color": "$brand.primary", "pad": "$space.md"}, "font": "$type.body"}
    assert validate_drift(obj, _TOKENS) == []


def test_validate_drift_flags_off_token_references():
    obj = {"color": "$brand.primary", "accent": "$brand.NEON", "shadow": "$fx.glow"}
    drift = validate_drift(obj, _TOKENS)
    assert set(drift) == {"brand.NEON", "fx.glow"}


def test_validate_drift_ignores_non_reference_strings():
    # a plain string that is not a "$token" reference is not drift (it is literal content)
    obj = {"label": "Ridgeline", "price": "$100 due"}  # "$100 due" is not a bare $token ref
    assert validate_drift(obj, _TOKENS) == []


# ---- apply_tokens: resolve + render through the Lens; refuse off-token ------------------------

def test_apply_tokens_resolves_and_renders_a_view():
    obj = {"header": {"color": "$brand.primary", "pad": "$space.md"}, "font": "$type.body"}
    view = apply_tokens(obj, _TOKENS)
    # composed the Lens -> a read-only View whose content carries the RESOLVED governed values
    assert view.content == {"header": {"color": "#0B2A4A", "pad": 16}, "font": "Arial 11pt"}


def test_apply_tokens_refuses_an_off_token_render():
    obj = {"color": "$brand.primary", "accent": "$brand.NEON"}
    with pytest.raises(TokenDrift):
        apply_tokens(obj, _TOKENS)  # deny-by-default: an off-token render is refused, not rendered


def test_apply_tokens_is_content_agnostic():
    # any object shape renders through the Lens after resolution
    obj = ["$brand.gold", {"x": "$space.md"}, "literal"]
    view = apply_tokens(obj, _TOKENS)
    assert view.content == ["#C7A24B", {"x": 16}, "literal"]


def test_apply_tokens_leaves_a_tokenless_object_unchanged():
    obj = {"title": "Ridgeline", "n": 3}
    view = apply_tokens(obj, _TOKENS)
    assert view.content == {"title": "Ridgeline", "n": 3}


def test_apply_tokens_privileges_no_token():
    # every declared token resolves; none is special-cased
    for name, value in _TOKENS.tokens.items():
        v = apply_tokens({"v": f"${name}"}, _TOKENS)
        assert v.content == {"v": value}


# ---- composition boundary: composes the Lens (Vol 1) ONLY ------------------------------------

def test_composes_the_lens_only():
    from sovereign_agent.sovereign_ux import tokens as tk
    from sovereign_agent.sovereign_ux.lens import render_view as rv
    assert tk.render_view is rv  # the Governed Aesthetic composes the Sovereign Lens, not a new renderer
    src = open(tk.__file__).read()
    assert "resonance" not in src.lower()          # never the s6_04 false-match
    assert "gate_interaction" not in src            # composes the Lens only, not V02
