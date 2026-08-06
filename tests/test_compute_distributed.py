"""Acceptance tests for Distributed Sovereign Compute (s6_03, S6 Vol 3) — a node offers governed capacity; a job is
admitted only by the node's declared consent + fail-closed on capacity. Composes the sealed object registry +
cross-mandate access check. Pure / structural (F-1 clean)."""
from decimal import Decimal

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.compute.distributed import offer_capacity, admit_job, ComputeError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _offer(reg, node="nodeA", units=100):
    return offer_capacity(reg, node, units, mandate=node, author=node, source_ref=f"cap://{node}/1", at="t")


def test_offer_capacity_registers_a_governed_offer(tmp_path):
    reg = _reg(tmp_path)
    o = _offer(reg)
    assert o["version_hash"]
    assert o["object_id"] == "capacity:nodeA"
    assert o["payload"]["units"] == "100"


def test_offer_capacity_refuses_empty_id_or_nonpositive_units(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ComputeError):
        offer_capacity(reg, "", 10, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    with pytest.raises(ComputeError):
        offer_capacity(reg, "nodeA", 0, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")


def test_admit_job_own_mandate_within_capacity(tmp_path):
    reg = _reg(tmp_path)
    o = _offer(reg, units=100)
    res = admit_job(reg, [], o, 40, requester_mandate="nodeA")  # own-mandate use is whole
    assert res["admitted"] is True
    assert res["remaining"] == "60"


def test_admit_job_refuses_over_subscription(tmp_path):
    reg = _reg(tmp_path)
    o = _offer(reg, units=100)
    with pytest.raises(ComputeError):
        admit_job(reg, [], o, 150, requester_mandate="nodeA")  # exceeds offered capacity


def test_admit_job_grants_a_declared_cross_node_crossing(tmp_path):
    reg = _reg(tmp_path)
    o = _offer(reg, node="nodeA", units=100)
    rules = [SharingRule("capacity:nodeA", "nodeB", "write")]
    res = admit_job(reg, rules, o, 30, requester_mandate="nodeB")
    assert res["admitted"] is True and res["remaining"] == "70"


def test_admit_job_refuses_undeclared_requester_or_unnamed(tmp_path):
    reg = _reg(tmp_path)
    o = _offer(reg, node="nodeA", units=100)
    with pytest.raises(ComputeError):
        admit_job(reg, [], o, 30, requester_mandate="nodeB")   # no declared crossing -> seized? refused
    with pytest.raises(ComputeError):
        admit_job(reg, [], o, 30, requester_mandate="   ")     # unnamed requester
