# -*- coding: utf-8 -*-
"""Acceptance tests for the Sovereign Lens (S8 Vol 1) — render_view.

Proves the kill-targets: renders never writes · content-agnostic · honest views / drift detection ·
multi-mandate scoped rendering (deny-by-default) · composes the node_api render seam. Crypto-free.
"""
import copy
import dataclasses
import datetime as _dt
import pytest

from sovereign_agent.sovereign_ux.lens import (
    render_view, verify_view, show, View, ViewStatus, LensDrift,
)


@dataclasses.dataclass
class _Obj:
    name: str
    amount: int
    tags: list


# ---- content-agnostic rendering (Ch2) --------------------------------------------------------

def test_render_dict_object():
    v = render_view({"a": 1, "b": [1, 2], "c": {"d": 3}})
    assert v.content == {"a": 1, "b": [1, 2], "c": {"d": 3}}
    assert v.object_type == "dict"


def test_render_dataclass_object():
    v = render_view(_Obj(name="ridgeline", amount=42, tags=["x", "y"]))
    assert v.content == {"name": "ridgeline", "amount": 42, "tags": ["x", "y"]}


def test_content_agnostic_privileges_none():
    # a custom attribute-carrier and a rich-typed object both render by structure, none privileged
    class Custom:
        def __init__(self):
            self.kind = "governed"
            self.when = _dt.datetime(2026, 8, 7, tzinfo=_dt.timezone.utc)
    v = render_view(Custom())
    assert v.content["kind"] == "governed"
    assert v.content["when"].startswith("2026-08-07")


# ---- renders, never writes (Ch2/Ch4 kill-target) ---------------------------------------------

def test_render_is_read_only():
    src = {"name": "x", "nested": {"k": [1, 2, 3]}}
    before = copy.deepcopy(src)
    v = render_view(src)
    # mutating the view's content must not touch the source
    v.content["nested"]["k"].append(999)
    v.content["name"] = "hacked"
    assert src == before  # source governed object is untouched


def test_view_is_frozen():
    v = render_view({"a": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.content = {"a": 2}  # type: ignore[misc]  — cannot write the object back through the Lens


# ---- honest views & drift detection (Ch3 kill-target) ----------------------------------------

def test_honest_view_fresh_when_unchanged():
    src = {"balance": 100}
    v = render_view(src)
    status = verify_view(v, src)
    assert status.fresh is True and status.drift is False
    assert show(v, src) == {"balance": 100}


def test_drift_detected_when_source_changes():
    src = {"balance": 100}
    v = render_view(src)
    src["balance"] = 250  # the governed object moved on after the view was rendered
    status = verify_view(v, src)
    assert status.drift is True and status.fresh is False


def test_drifted_view_is_never_silently_shown():
    src = {"balance": 100}
    v = render_view(src)
    src["balance"] = 250
    with pytest.raises(LensDrift):
        show(v, src)  # a stale view is refused, not silently displayed


# ---- multi-mandate scoped rendering (Ch5 kill-target, S5 Vol 28) ------------------------------

_SCOPE = {"treasury": ["balance", "currency"], "audit": ["balance", "audit_ref"]}


def test_scoped_by_mandate_withholds_out_of_scope_fields():
    src = {"balance": 100, "currency": "USD", "audit_ref": "A-1", "secret": "x"}
    v = render_view(src, mandate="treasury", scope=_SCOPE)
    assert v.content == {"balance": 100, "currency": "USD"}
    assert "secret" not in v.content and "audit_ref" not in v.content


def test_multi_mandate_distinct_views():
    src = {"balance": 100, "currency": "USD", "audit_ref": "A-1", "secret": "x"}
    treasury = render_view(src, mandate="treasury", scope=_SCOPE)
    audit = render_view(src, mandate="audit", scope=_SCOPE)
    assert treasury.content == {"balance": 100, "currency": "USD"}
    assert audit.content == {"balance": 100, "audit_ref": "A-1"}


def test_unknown_mandate_is_deny_by_default():
    src = {"balance": 100, "currency": "USD"}
    v = render_view(src, mandate="stranger", scope=_SCOPE)
    assert v.content == {}  # an un-mapped mandate is admitted nothing


def test_unscoped_renders_all_backward_compatible():
    src = {"balance": 100, "currency": "USD", "secret": "x"}
    v = render_view(src)  # single-mandate node: no scope → full render
    assert v.content == src and v.fields is None


# ---- composition boundary (proves it composes the sealed node_api seam) -----------------------

def test_composes_node_api_jsonable_seam():
    from sovereign_agent.sovereign_ux import lens as _lens
    from sovereign_agent.node_api.json_provider import _to_jsonable as seam
    assert _lens._to_jsonable is seam  # the render seam is composed, not re-implemented


def test_render_seam_raises_rather_than_losing_structure():
    # TRUTH > silent: a truly unserialisable object surfaces the node_api seam's explicit failure
    class Opaque:
        __slots__ = ()
    with pytest.raises(TypeError):
        render_view(Opaque())
