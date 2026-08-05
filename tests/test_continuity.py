"""Generational Continuity (s5_27 / reading Vol 29) — proof that a generational handoff is a transfer of PROOF: a
self-verifying successor package, handed over only through a human gate, composing the sealed Sovereign Object Model
and building no successor-packet engine of its own.

Pure composition (the object model is hashlib-based, no crypto substrate) — runs green on a bare public clone."""
import pytest

from sovereign_agent import continuity as cont
from sovereign_agent.continuity import HandoffError
from sovereign_agent.objects.registry import ObjectRegistry

SRC = "continuity-handoff:concord"  # symbolic source citation — accepted as-is by the object model


def _registry(tmp_path):
    reg = ObjectRegistry(str(tmp_path / "estate"))
    reg.append("holding:H1", {"name": "Ridgeline", "value": "100"}, author="steward",
               source_ref=SRC, at="2026-08-05", mandate="estate")
    reg.append("holding:H2", {"name": "Harbor", "value": "40"}, author="steward",
               source_ref=SRC, at="2026-08-05", mandate="estate")
    return reg


def test_assemble_successor_package_self_verifies(tmp_path):
    reg = _registry(tmp_path)
    pkg = cont.assemble_successor_package(reg, at="2026-08-05")
    out = cont.govern_handoff(pkg, approver="elder-jane", approval_ref="minute:2026-08-05#ratified")
    assert out["handed_off"] is True and out["verified"] is True
    assert out["package_root"] == pkg["manifest"]["root"]
    assert out["approver"] == "elder-jane"


def test_govern_handoff_refuses_a_tampered_package(tmp_path):
    reg = _registry(tmp_path)
    pkg = cont.assemble_successor_package(reg, at="2026-08-05")
    pkg["objects"][0]["payload"]["value"] = "999999"  # someone dressed up a holding after assembly
    with pytest.raises(HandoffError, match="does not verify"):
        cont.govern_handoff(pkg, approver="elder-jane", approval_ref="minute:1#r")


def test_govern_handoff_refuses_with_no_named_approver(tmp_path):
    reg = _registry(tmp_path)
    pkg = cont.assemble_successor_package(reg, at="2026-08-05")
    with pytest.raises(HandoffError, match="named human approver"):
        cont.govern_handoff(pkg, approver="", approval_ref="minute:1#r")


def test_govern_handoff_refuses_with_no_approval_reference(tmp_path):
    reg = _registry(tmp_path)
    pkg = cont.assemble_successor_package(reg, at="2026-08-05")
    with pytest.raises(HandoffError, match="approval reference"):
        cont.govern_handoff(pkg, approver="elder-jane", approval_ref="")
