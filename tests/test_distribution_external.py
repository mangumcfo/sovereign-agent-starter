"""Social & External Distribution (s5_30 / reading Vol 32) — governed content distribution with provenance."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.distribution.external import publish_content, govern_distribution, DistributionError

SRC = "content:ridgeline-statement-2026"  # symbolic provenance (not a path)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "channel"))


def test_publish_content_registers_a_governed_object_with_provenance(tmp_path):
    reg = _reg(tmp_path)
    publish_content(reg, "statement", {"body": "the family's public note"},
                    mandate="ridgeline", author="steward", source_ref=SRC, at="2026-08-05")
    cur = reg.current()["content:statement"]
    assert cur["payload"]["body"] == "the family's public note"
    assert cur["mandate"] == "ridgeline" and cur["kind"] == "ratify" and cur["version_hash"]
    assert cur["source_ref"] == SRC  # the content carries its provenance


def test_publish_content_refuses_empty_id_or_payload(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(DistributionError, match="needs an id"):
        publish_content(reg, "", {"body": "x"}, mandate="r", author="s", source_ref=SRC, at="2026-08-05")
    with pytest.raises(DistributionError, match="needs a payload"):
        publish_content(reg, "empty", {}, mandate="r", author="s", source_ref=SRC, at="2026-08-05")


def test_govern_distribution_distributes_and_carries_provenance(tmp_path):
    reg = _reg(tmp_path)
    publish_content(reg, "statement", {"body": "note"}, mandate="ridgeline",
                    author="steward", source_ref=SRC, at="2026-08-05")
    content = reg.current()["content:statement"]
    r = govern_distribution(content, approver="comms-steward", approval_ref="publish-vote:2026-08-05")
    assert r["distributed"] is True
    assert r["provenance"] == SRC and r["content_root"] == content["version_hash"]
    assert r["approver"] == "comms-steward"


def test_govern_distribution_refuses_ungoverned_content(tmp_path):
    with pytest.raises(DistributionError, match="no governed content"):
        govern_distribution({"body": "raw"}, approver="s", approval_ref="ref")  # no version_hash


def test_govern_distribution_refuses_with_no_named_approver(tmp_path):
    reg = _reg(tmp_path)
    publish_content(reg, "statement", {"body": "note"}, mandate="ridgeline",
                    author="steward", source_ref=SRC, at="2026-08-05")
    content = reg.current()["content:statement"]
    with pytest.raises(DistributionError, match="named human approver"):
        govern_distribution(content, approver="   ", approval_ref="publish-vote:2026-08-05")


def test_govern_distribution_refuses_with_no_approval_reference(tmp_path):
    reg = _reg(tmp_path)
    publish_content(reg, "statement", {"body": "note"}, mandate="ridgeline",
                    author="steward", source_ref=SRC, at="2026-08-05")
    content = reg.current()["content:statement"]
    with pytest.raises(DistributionError, match="approval reference"):
        govern_distribution(content, approver="comms-steward", approval_ref="")
