# -*- coding: utf-8 -*-
"""Proof-first tests for peerhood.bridging (S14 Vol 4:
Bridging into Pools & Federations).

Kill-targets pinned:
- composes sealed floors + peerhood layers ONLY (S14 V01 genesis · S14 V02 recognition · D1 keystore · S6 V1
  send_message · S10 V2 form_pool/contribute_to_pool/pool_settlement · S11 V4 enforce_decision · S5 V16 gate);
  invents no mechanism; rolls no crypto;
- form_peer_pool composes S10 V2 form_pool (pool holds no value, no custodian); membership is the peer's OWN
  reversible record signed with its key — NOT a token a hub holds;
- bridge_into_pool is a receipted bridge (S6 V1) signed with the key, verifiable (public-only) + REVERSIBLE;
- federate_without_directory composes the sealed S14 V02 directory-free discovery — NO central directory;
- attribute_pool_value records earned value as the MEMBER's OWN receipt (S10 V2/V1); settle_pool_on_port settles
  ONLY via the Port (S10 V2 pool_settlement) — an in-node pool-balance/held-value field is refused;
- pool_vote is HUMAN-GATED (no approver refused) + signed (S11 V4 over S5 V16);
- KILL-TARGET: a bridging-hub / membership-token / central-settlement / netting / registry / custodian field is
  refused (BRIDGING_BREACH_FIELDS).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.pool import PoolSettlement
from sovereign_agent.peerhood.genesis import establish_self_held_identity, PeerhoodError
from sovereign_agent.peerhood.bridging import (
    form_peer_pool, bridge_into_pool, verify_bridge, federate_without_directory,
    attribute_pool_value, settle_pool_on_port, pool_vote, BRIDGING_BREACH_FIELDS,
)

AT = "2026-08-11T17:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _peers(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    b = establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    return ks, reg, a, b


def test_form_peer_pool_holds_no_value_membership_is_own_reversible_record(tmp_path):
    ks, reg, a, b = _peers(tmp_path)
    pool, mem = form_peer_pool(ks, "pool-1", ["peer-a", "peer-b"], "peer-a")
    assert pool.members == ("peer-a", "peer-b")                                # S10 V2 pool: who is in, no value
    assert mem["reversible"] is True and mem["token_held_by_third_party"] is None and mem["membership_sig"]
    with pytest.raises(PeerhoodError):                                         # no key -> cannot join
        form_peer_pool(str(tmp_path / "empty"), "pool-1", ["ghost", "peer-b"], "ghost")


def test_bridge_into_pool_is_receipted_verifiable_and_reversible(tmp_path):
    ks, reg, a, b = _peers(tmp_path)
    br = bridge_into_pool(ks, "peer-a", "pool-1", at=AT, registry=reg)
    assert br["reversible"] is True and br["hub"] is None and br["signature"]
    assert verify_bridge(br, a) is True                                       # both sides verify, public-only
    assert verify_bridge(br, b) is False                                      # a different peer does not verify
    with pytest.raises(PeerhoodError):
        bridge_into_pool(str(tmp_path / "empty"), "ghost", "pool-1", at=AT, registry=reg)


def test_federate_without_a_directory(tmp_path):
    fed = federate_without_directory("root-abc", "root-abc")
    assert fed["federated"] is True and fed["aligned"] is True and fed["central_directory"] is None
    assert federate_without_directory("root-abc", "root-xyz")["aligned"] is False
    with pytest.raises(PeerhoodError):
        federate_without_directory("root-abc", "root-abc", extra={"directory": "acme"})


def test_value_attribution_is_an_owned_receipt_settled_only_on_the_port(tmp_path):
    ks, reg, a, b = _peers(tmp_path)
    pool, _ = form_peer_pool(ks, "pool-1", ["peer-a", "peer-b"], "peer-a")
    val = attribute_pool_value(pool, "peer-a", "client", "w1", at=AT, registry=reg, amount="100", port_ref="port:1")
    assert val.get("mandate") == "peer-a"                                     # the MEMBER owns the receipt
    st = settle_pool_on_port(pool, [("peer-a", {"share": "50", "port_ref": "port:a"}),
                                    ("peer-b", {"share": "50", "port_ref": "port:b"})])
    assert isinstance(st, PoolSettlement)                                     # settled via the Port, per member
    with pytest.raises(Exception):                                            # an in-node pool-value settlement refused
        settle_pool_on_port(pool, [("peer-a", {"share": "50", "pool_balance": 999})])


def test_pool_vote_is_human_gated_and_signed(tmp_path):
    ks, reg, a, b = _peers(tmp_path)
    with pytest.raises(PeerhoodError):                                        # human-gated — no approver refused
        pool_vote(ks, "peer-a", "pool-1", "admit_member", "w-vote", at=AT, registry=reg,
                  gate=HumanApprovalGate(), approver="", approval_ref="b:1")
    v = pool_vote(ks, "peer-a", "pool-1", "admit_member", "w-vote", at=AT, registry=reg,
                  gate=HumanApprovalGate(), approver="km-1176", approval_ref="b:1")
    assert v["human_gated"] is True and v["signature"] and v["peer_id"] == "peer-a"


def test_the_fence_refuses_hub_membership_token_and_central_settlement(tmp_path):
    ks, reg, a, b = _peers(tmp_path)
    for bad in ("bridging_hub", "membership_token", "central_settlement", "netting", "pool_balance",
                "registry", "custodian"):
        with pytest.raises(PeerhoodError):
            bridge_into_pool(ks, "peer-a", "pool-1", at=AT, registry=reg, extra={bad: "acme"})
    assert {"bridging_hub", "membership_token", "central_settlement", "registry"} <= BRIDGING_BREACH_FIELDS


def test_composes_sealed_floors_and_peerhood():
    import sovereign_agent.peerhood.bridging as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("genesis", "recognition", "keystore", "messaging.inter_node",
                   "economy.pool", "risk.governance"):
        assert sealed in src                                                  # composes S14 V01/V02 + D1 + S6 + S10 + S11
