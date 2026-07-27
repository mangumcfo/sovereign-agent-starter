"""S5-05-E1-2 · E5-1 · E5-2 · E5-4: the governed lifecycle."""
import pytest
from sovereign_agent.objects.lifecycle import (Closed, Envelope, EnvelopeRefusal,
                                               apply_change, close_object, value_at)
from sovereign_agent.objects.registry import ObjectRegistry


def _reg(tmp_path):
    reg = ObjectRegistry(str(tmp_path))
    reg.append("customer:C-1042", {"name": "Halvorsen Industrial", "limit": 150000},
               author="d.reyes", source_ref="APP-1042:credit app", at="2029-03-01",
               mandate="operating")
    return reg


def test_value_at_date_returns_prior_value_and_approver(tmp_path):
    reg = _reg(tmp_path)
    apply_change(reg, "customer:C-1042", {"limit": 250000}, author="d.reyes",
                 source_ref="MEMO-0314:credit memo", at="2029-03-14",
                 approver="controller", approval_ref="CM-88")
    payload, approver, v = value_at(reg, "customer:C-1042", "2029-03-10")
    assert payload["limit"] == 150000 and approver is None
    payload, approver, v = value_at(reg, "customer:C-1042", "2029-03-14")
    assert payload["limit"] == 250000 and approver == "controller"


def test_change_appends_version_and_prior_version_unchanged(tmp_path):
    reg = _reg(tmp_path)
    before = reg.versions("customer:C-1042")[0]
    apply_change(reg, "customer:C-1042", {"limit": 200000}, author="d.reyes",
                 source_ref="MEMO-2:credit memo", at="2029-04-01")
    after = reg.versions("customer:C-1042")
    assert len(after) == 2 and after[1]["seq"] == 2
    assert after[0] == before  # prior version byte-for-byte untouched
    assert after[1]["prev_hash"] == before["version_hash"]


def test_out_of_envelope_change_refused_with_rule_cited(tmp_path):
    reg = _reg(tmp_path)
    env = Envelope({"limit": {"max_delta": 50000}})
    with pytest.raises(EnvelopeRefusal) as ei:
        apply_change(reg, "customer:C-1042", {"limit": 400000}, author="d.reyes",
                     source_ref="MEMO-3:credit memo", at="2029-04-02", envelope=env)
    assert "limit.max_delta=50000" in str(ei.value)  # the rule is CITED
    assert len(reg.versions("customer:C-1042")) == 1  # nothing silently applied
    # the same change WITH a human-gated approval appends
    v = apply_change(reg, "customer:C-1042", {"limit": 400000}, author="d.reyes",
                     source_ref="MEMO-3:credit memo", at="2029-04-02", envelope=env,
                     approver="km-1176", approval_ref="GATE-77")
    assert v["approver"] == "km-1176"


def test_close_is_a_version_and_history_remains_readable(tmp_path):
    reg = _reg(tmp_path)
    close_object(reg, "customer:C-1042", author="d.reyes",
                 source_ref="CLOSE-1:retirement memo", at="2030-01-01")
    vs = reg.versions("customer:C-1042")
    assert vs[-1]["kind"] == "close" and len(vs) == 2  # a version, not a deletion
    payload, _, _ = value_at(reg, "customer:C-1042", "2029-06-01")
    assert payload["limit"] == 150000  # history readable after close
    with pytest.raises(Closed):
        apply_change(reg, "customer:C-1042", {"limit": 1}, author="x",
                     source_ref="X-1:memo", at="2030-02-01")
