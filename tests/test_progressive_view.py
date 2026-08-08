# -*- coding: utf-8 -*-
"""Acceptance tests for Generational UX (S8 Vol 5) — progressive_view.

Proves the surface renders the SAME governed object at different complexity levels: a simpler level omits
fields but never distorts values; the handoff level shows the whole object; an unknown level shows
nothing (deny-by-default); rendering is read-only; and every level's View fingerprints the FULL object,
so a simple view detects drift in the whole exactly as the handoff view would (weakest-party
verifiability — a green light from verify_level proves the level matches the current whole). Composes the
Lens only. Crypto-free.
"""
import dataclasses
import pytest

from sovereign_agent.sovereign_ux.progressive_view import (
    progressive_view, handoff_view, verify_level, LevelSet, HANDOFF)
from sovereign_agent.sovereign_ux.lens import View


_OBJ = {"name": "Ridgeline Trust", "balance": 1000, "counsel": "priv-note", "detail": {"k": 1}}
_LEVELS = LevelSet(levels={"novice": ["name"], "operator": ["name", "balance"]})


# ---- the same object at every level; a simpler level omits but never distorts ----------------

def test_renders_same_object_at_a_level():
    v = progressive_view(_OBJ, _LEVELS, level="operator")
    assert v.content == {"name": "Ridgeline Trust", "balance": 1000}   # operator sees name + balance
    assert isinstance(v, View)


def test_simpler_level_omits_but_does_not_distort():
    novice = progressive_view(_OBJ, _LEVELS, level="novice")
    assert novice.content == {"name": "Ridgeline Trust"}               # fewer fields...
    assert novice.content["name"] == _OBJ["name"]                      # ...but the value is the object's own, not altered


def test_handoff_level_shows_the_whole_object():
    v = progressive_view(_OBJ, _LEVELS, level=HANDOFF)
    assert v.content == _OBJ                                           # the successor sees everything, omits nothing


def test_handoff_view_helper_shows_whole_object():
    assert handoff_view(_OBJ).content == _OBJ


def test_unknown_level_shows_nothing_deny_by_default():
    v = progressive_view(_OBJ, _LEVELS, level="wizard")               # undeclared level
    assert v.content == {}                                            # deny-by-default: nothing


# ---- read-only ------------------------------------------------------------------------------

def test_rendering_is_read_only():
    v = progressive_view(_OBJ, _LEVELS, level="operator")
    v.content["balance"] = 0                                          # mutate the rendered view
    assert _OBJ["balance"] == 1000                                    # the source object is untouched


# ---- weakest-party verifiability: every level fingerprints the FULL object -------------------

def test_full_object_fingerprint_regardless_of_level():
    # a novice view and a handoff view of the same object share the same (full-object) fingerprint
    novice = progressive_view(_OBJ, _LEVELS, level="novice")
    whole = handoff_view(_OBJ)
    assert novice.fingerprint == whole.fingerprint


def test_simple_level_detects_drift_in_the_whole():
    # weakest-party check: a person who can only read fresh/drift can trust a simple view isn't hiding a
    # changed object — verify_level on a NOVICE view flags a change to a field the novice never saw.
    novice = progressive_view(_OBJ, _LEVELS, level="novice")
    moved = dict(_OBJ, counsel="CHANGED")                             # a field outside the novice level moved
    status = verify_level(novice, moved)
    assert status.drift and not status.fresh                          # the simple view still detects the whole's drift
    assert verify_level(novice, _OBJ).fresh                           # unchanged -> fresh (a green light)


# ---- no second authority · composition boundary ---------------------------------------------

def test_imports_only_lens_no_engine():
    from sovereign_agent.sovereign_ux import progressive_view as pv
    import_lines = [ln for ln in open(pv.__file__).read().splitlines()
                    if ln.strip().startswith(("from ", "import ")) and "__future__" not in ln]
    joined = " ".join(import_lines)
    tokens = joined.replace("from", " ").replace("import", " ")
    assert ".lens" in joined
    for banned in ("continuity", "onboarding", "atrium", "estate", "transfer", "crypto", "hashlib"):
        assert banned not in tokens, f"progressive_view must not import a floor/engine: {banned}"


def test_level_set_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _LEVELS.levels = {}   # type: ignore[misc]


def test_composes_the_lens_by_identity():
    from sovereign_agent.sovereign_ux import progressive_view as pv
    from sovereign_agent.sovereign_ux.lens import render_view as rv, verify_view as vv
    assert pv.render_view is rv and pv.verify_view is vv
