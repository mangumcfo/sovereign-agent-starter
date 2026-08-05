"""Federation Marketplace (s5_31 / reading Vol 33) — verified blueprints published and consumed under governance."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.marketplace import publish_blueprint, govern_consumption, MarketplaceError

SRC = "blueprint:erp-close-pattern-v1"  # symbolic provenance (not a path)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "marketplace"))


def test_publish_blueprint_registers_a_governed_object(tmp_path):
    reg = _reg(tmp_path)
    publish_blueprint(reg, "monthly-close", {"steps": "reconcile · accrue · report"},
                      mandate="north-guild", author="author-node", source_ref=SRC, at="2026-08-05")
    cur = reg.current()["blueprint:monthly-close"]
    assert cur["payload"]["pattern"]["steps"].startswith("reconcile")
    assert cur["mandate"] == "north-guild" and cur["kind"] == "ratify" and cur["version_hash"]


def test_publish_blueprint_refuses_empty_id_or_pattern(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(MarketplaceError, match="needs an id"):
        publish_blueprint(reg, "", {"steps": "x"}, mandate="g", author="a", source_ref=SRC, at="2026-08-05")
    with pytest.raises(MarketplaceError, match="needs a pattern"):
        publish_blueprint(reg, "empty", {}, mandate="g", author="a", source_ref=SRC, at="2026-08-05")


def test_govern_consumption_adopts_on_a_named_human(tmp_path):
    reg = _reg(tmp_path)
    publish_blueprint(reg, "monthly-close", {"steps": "reconcile"}, mandate="north-guild",
                      author="author-node", source_ref=SRC, at="2026-08-05")
    version = reg.current()["blueprint:monthly-close"]["version_hash"]
    r = govern_consumption(reg, "monthly-close", approver="river-coop-lead", approval_ref="adopt-minute:2026-08-06")
    assert r["consumed"] is True and r["blueprint"] == "monthly-close"
    assert r["version"] == version and r["approver"] == "river-coop-lead"


def test_govern_consumption_refuses_a_nonexistent_blueprint(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(MarketplaceError, match="no such published blueprint"):
        govern_consumption(reg, "ghost", approver="a", approval_ref="ref")


def test_govern_consumption_refuses_with_no_named_approver(tmp_path):
    reg = _reg(tmp_path)
    publish_blueprint(reg, "monthly-close", {"steps": "reconcile"}, mandate="north-guild",
                      author="author-node", source_ref=SRC, at="2026-08-05")
    with pytest.raises(MarketplaceError, match="named human approver"):
        govern_consumption(reg, "monthly-close", approver="  ", approval_ref="adopt-minute:2026-08-06")


def test_govern_consumption_refuses_with_no_approval_reference(tmp_path):
    reg = _reg(tmp_path)
    publish_blueprint(reg, "monthly-close", {"steps": "reconcile"}, mandate="north-guild",
                      author="author-node", source_ref=SRC, at="2026-08-05")
    with pytest.raises(MarketplaceError, match="approval reference"):
        govern_consumption(reg, "monthly-close", approver="river-coop-lead", approval_ref="")
