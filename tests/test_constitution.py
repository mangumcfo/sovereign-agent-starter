"""Private Series Templates (s5_28 / reading Vol 30) — proof that a constitution is a governed object whose core is
protected and whose amendments are governed versions, composing the sealed Sovereign Object Model and building no
constitution store or amendment engine of its own.

Pure composition (the object model is hashlib-based, no crypto substrate) — runs green on a bare public clone."""
import pytest

from sovereign_agent import constitution as con
from sovereign_agent.constitution import ConstitutionError
from sovereign_agent.objects.lifecycle import EnvelopeRefusal
from sovereign_agent.objects.registry import ObjectRegistry

SRC = "constitution:concord-family"


def _reg_with_constitution(tmp_path):
    reg = ObjectRegistry(str(tmp_path / "family"))
    con.open_constitution(reg, "concord", {"succession": "equal", "values": "stewardship", "quorum": "3"},
                          mandate="family-concord", author="founder", source_ref=SRC, at="2026-08-05")
    return reg


def test_open_constitution_registers_a_governed_object(tmp_path):
    reg = _reg_with_constitution(tmp_path)
    cur = reg.current()["constitution:concord"]
    assert cur["payload"]["succession"] == "equal" and cur["mandate"] == "family-concord"
    assert cur["version_hash"] and cur["kind"] == "ratify"


def test_amend_inside_the_envelope_is_a_governed_version(tmp_path):
    reg = _reg_with_constitution(tmp_path)
    env = con.core_envelope({"succession": {"allowed": ["equal", "primogeniture"]}})
    v = con.amend(reg, "concord", {"succession": "primogeniture"}, envelope=env,
                  author="council", source_ref=SRC, at="2026-08-06")
    assert v["payload"]["succession"] == "primogeniture" and v["seq"] == 2  # a new version, prior preserved
    assert len(reg.versions("constitution:concord")) == 2


def test_amend_a_core_article_beyond_the_envelope_is_refused_fail_closed(tmp_path):
    reg = _reg_with_constitution(tmp_path)
    env = con.core_envelope({"succession": {"allowed": ["equal", "primogeniture"]}})
    # "dictatorship" is not an allowed succession — refused, and prior versions untouched
    with pytest.raises(EnvelopeRefusal, match="succession"):
        con.amend(reg, "concord", {"succession": "dictatorship"}, envelope=env,
                  author="usurper", source_ref=SRC, at="2026-08-06")
    assert len(reg.versions("constitution:concord")) == 1  # nothing appended


def test_amend_beyond_the_envelope_is_allowed_with_a_human_gated_approval(tmp_path):
    reg = _reg_with_constitution(tmp_path)
    env = con.core_envelope({"succession": {"allowed": ["equal", "primogeniture"]}})
    # a core change beyond the envelope proceeds ONLY with a named approver + approval reference
    v = con.amend(reg, "concord", {"succession": "council-appointed"}, envelope=env,
                  author="council", source_ref=SRC, at="2026-08-07",
                  approver="family-elders", approval_ref="family-vote:2026-08-07")
    assert v["payload"]["succession"] == "council-appointed" and v["approver"] == "family-elders"


def test_a_non_core_article_amends_freely_within_the_version_discipline(tmp_path):
    reg = _reg_with_constitution(tmp_path)
    env = con.core_envelope({"succession": {"allowed": ["equal", "primogeniture"]}})
    # "values" is not named core -> amends freely, still as a governed version
    v = con.amend(reg, "concord", {"values": "stewardship and enterprise"}, envelope=env,
                  author="council", source_ref=SRC, at="2026-08-06")
    assert v["payload"]["values"] == "stewardship and enterprise" and v["seq"] == 2
