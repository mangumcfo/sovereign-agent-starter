"""Acceptance tests for Shields as Protective Layers (s7_02, S7 Vol 2) — layered, independently-verifiable protections
over a resource, deny-by-default (defense in depth). The integrity shield composes the sealed P5 Merkle substrate
(vendored in-tree, via the _lazy_bp boundary). No second trust authority, no central attestation, no vouching hub."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.shields.protective import declare_shield, pass_shield_stack, ShieldError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _integrity(reg, resource="doc:1", chunks=(b"alpha", b"beta", b"gamma")):
    return declare_shield(reg, resource, "integrity", list(chunks), mandate="nodeA",
                          author="nodeA", source_ref=f"shield://{resource}", at="2026-08-06")


def test_declare_shield_integrity_registers_governed_object_with_root(tmp_path):
    reg = _reg(tmp_path)
    s = _integrity(reg)
    assert s["version_hash"]
    assert s["object_id"] == "shield:doc:1:integrity"
    assert s["payload"]["kind"] == "integrity" and s["payload"]["root"]  # Merkle root over the chunks (P5)


def test_declare_shield_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ShieldError):
        declare_shield(reg, "", "integrity", [b"x"], mandate="nodeA", author="nodeA", source_ref="s://1", at="t")
    with pytest.raises(ShieldError):
        declare_shield(reg, "doc:1", "", [b"x"], mandate="nodeA", author="nodeA", source_ref="s://1", at="t")
    with pytest.raises(ShieldError):
        declare_shield(reg, "doc:1", "integrity", [], mandate="nodeA", author="nodeA", source_ref="s://1", at="t")


def test_pass_shield_stack_clears_matching_payload(tmp_path):
    reg = _reg(tmp_path)
    s = _integrity(reg, chunks=(b"alpha", b"beta", b"gamma"))
    res = pass_shield_stack([s], [b"alpha", b"beta", b"gamma"])  # same bytes -> same Merkle root
    assert res["cleared"] is True and res["layers"] == 1 and res["kinds"] == ["integrity"]


def test_pass_shield_stack_refuses_tampered_payload(tmp_path):
    reg = _reg(tmp_path)
    s = _integrity(reg, chunks=(b"alpha", b"beta", b"gamma"))
    with pytest.raises(ShieldError):
        pass_shield_stack([s], [b"alpha", b"beta", b"TAMPERED"])  # altered -> Merkle root mismatch


def test_pass_shield_stack_deny_by_default_empty(tmp_path):
    with pytest.raises(ShieldError):
        pass_shield_stack([], [b"x"])  # no declared shield -> not implicitly open


def test_pass_shield_stack_refuses_unknown_kind(tmp_path):
    reg = _reg(tmp_path)
    bogus = reg.append("shield:doc:1:mystery", {"kind": "mystery", "resource": "doc:1"},
                       author="nodeA", source_ref="s://1", at="t", mandate="nodeA", kind="ratify")
    with pytest.raises(ShieldError):
        pass_shield_stack([bogus], [b"x"])  # unknown protection is not silently passed


def test_pass_shield_stack_defense_in_depth_all_must_pass(tmp_path):
    # two integrity shields over the same resource; if the payload fails either layer the whole stack refuses
    reg = _reg(tmp_path)
    s1 = declare_shield(reg, "doc:2", "integrity", [b"one", b"two"], mandate="nodeA",
                        author="nodeA", source_ref="s://2a", at="t")
    s2 = _integrity(reg, resource="doc:2b", chunks=(b"one", b"two"))
    assert pass_shield_stack([s1, s2], [b"one", b"two"])["layers"] == 2
    with pytest.raises(ShieldError):
        pass_shield_stack([s1, s2], [b"one", b"CHANGED"])
