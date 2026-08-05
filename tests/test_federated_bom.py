"""Distributed Manufacturing (s5_39 / reading Vol 41) — the federated BOM as a governed, forkable object."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.manufacturing.federated_bom import open_bom, fork_bom, bom_root, BOMError

SRC = "bom:drone-frame-spec-v1"  # symbolic provenance (not a path)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "factory"))


def test_open_bom_registers_a_governed_object(tmp_path):
    reg = _reg(tmp_path)
    open_bom(reg, "drone-frame", {"tube": "6061-al x4", "bracket": "printed x4"},
             mandate="guild-north", author="engineer", source_ref=SRC, at="2026-08-05")
    cur = reg.current()["bom:drone-frame"]
    assert cur["payload"]["parts"]["tube"] == "6061-al x4"
    assert cur["mandate"] == "guild-north" and cur["kind"] == "ratify" and cur["version_hash"]


def test_open_bom_refuses_empty_id_or_empty_parts(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(BOMError, match="needs an id"):
        open_bom(reg, "", {"tube": "x"}, mandate="g", author="e", source_ref=SRC, at="2026-08-05")
    with pytest.raises(BOMError, match="at least one part"):
        open_bom(reg, "empty", {}, mandate="g", author="e", source_ref=SRC, at="2026-08-05")


def test_fork_bom_cites_its_parent_and_leaves_it_untouched(tmp_path):
    reg = _reg(tmp_path)
    open_bom(reg, "drone-frame", {"tube": "6061-al x4"},
             mandate="guild-north", author="engineer", source_ref=SRC, at="2026-08-05")
    parent_v = reg.current()["bom:drone-frame"]["version_hash"]
    fork_bom(reg, "drone-frame", new_id="drone-frame-heavy",
             author="fabricator", source_ref="bom:fork-note", at="2026-08-06")
    fork = reg.current()["bom:drone-frame-heavy"]
    assert fork["payload"]["forked_from"] == "drone-frame"
    assert fork["payload"]["forked_at_version"] == parent_v
    assert len(reg.versions("bom:drone-frame")) == 1  # the parent is never touched


def test_fork_of_a_nonexistent_bom_is_refused(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(BOMError, match="no such bill of materials"):
        fork_bom(reg, "ghost", new_id="ghost-2", author="f", source_ref="bom:x", at="2026-08-05")


def test_bom_root_is_an_assembly_identity_that_moves_with_the_parts(tmp_path):
    reg = _reg(tmp_path)
    open_bom(reg, "drone-frame", {"tube": "6061-al x4"},
             mandate="guild-north", author="engineer", source_ref=SRC, at="2026-08-05")
    r1 = bom_root(reg, at="2026-08-05")
    open_bom(reg, "landing-gear", {"skid": "printed x2"},
             mandate="guild-north", author="engineer", source_ref="bom:gear-spec", at="2026-08-06")
    r2 = bom_root(reg, at="2026-08-06")
    assert r1 and r2 and r1 != r2  # the assembly identity changes when the governed parts change
