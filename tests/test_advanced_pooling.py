# -*- coding: utf-8 -*-
"""Proof-first tests for risk.advanced_pooling (S11 Vol 2, Advanced Pooling, Credit Mechanics & Proof Systems).

Kill-targets pinned:
- composes the sealed S11 V1 (mutual_protection) + S10 contribution floors ONLY — invents no new engine, rolls
  no cryptography (the range-proof crypto homes OUT to the sealed ZK shield, S7);
- a FEDERATION bridges >=2 pools, holds no value, members = union; a member settles across it ONLY via the Port;
- SELECTIVE DISCLOSURE reveals a chosen subset of a member's own verified receipts, withholds the rest,
  complete iff the disclosed verify; an out-of-range index or a foreign disclosed record is refused/breaks it;
- a multi-party ATTESTATION CHAIN verifies end to end; a reordered/tampered chain or wrong length fails;
- the S11 fence is inherited (no in-node custody on a bridge settlement); weakest-party plain bool.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.risk.mutual_protection import form_protection_pool, record_premium, IncomeRefused
from sovereign_agent.risk.advanced_pooling import (
    federate_pools, bridge_settlement, selective_disclosure, build_attestation_chain, verify_attestation_chain,
    Federation, DisclosedCredit, RISK_BREACH_FIELDS,
)

A, B, C, AUTHOR, AT = "ridgeline-kenn", "cedar-partner", "granite-neighbor", "Kenneth Mangum", "2026-08-10T05:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _two_pools():
    return form_protection_pool("ridgeline-aid", (A, B)), form_protection_pool("valley-aid", (B, C))


def test_a_federation_bridges_two_pools_holds_no_value_members_union(tmp_path):
    p1, p2 = _two_pools()
    fed = federate_pools("mountain-federation", (p1, p2))
    assert isinstance(fed, Federation) and set(fed.members) == {A, B, C}
    assert fed.has(A) and fed.has(C)
    with pytest.raises(IncomeRefused):        # a federation of one pool is not a federation
        federate_pools("solo", (p1,))
    assert not hasattr(fed, "balance") and not hasattr(fed, "value")


def test_a_member_settles_across_the_federation_only_via_the_port(tmp_path):
    p1, p2 = _two_pools()
    fed = federate_pools("mountain-federation", (p1, p2))
    s = bridge_settlement(fed, A, {"share": "200 credits", "port_ref": "PortDirective:bridge-1"})
    assert s.directives[0]["member"] == A and s.directives[0]["port_ref"] == "PortDirective:bridge-1"
    with pytest.raises(IncomeRefused):        # no Port directive -> refused (settles ONLY via the Port)
        bridge_settlement(fed, A, {"share": "200 credits"})
    with pytest.raises(IncomeRefused):        # a non-member cannot be settled
        bridge_settlement(fed, "stranger", {"share": "1", "port_ref": "PortDirective:x"})
    with pytest.raises(IncomeRefused):        # an in-node custody field is refused (S11 fence inherited)
        bridge_settlement(fed, A, {"share": "1", "port_ref": "PortDirective:x", "reserve": True})


def _premium_records(reg, pool, member, n):
    recs = []
    for i in range(n):
        r = record_premium(pool, member, f"prem-{i}", contribution_class="attested", author=AUTHOR,
                           source_ref="s", at=AT, registry=reg, amount=10.0 + i)
        recs.append({"receipt": r, "work_ref": f"prem-{i}", "contribution_class": "attested",
                     "source": "premium", "amount": 10.0 + i, "extra": {"pool": pool.pool_id}})
    return recs


def test_selective_disclosure_reveals_a_subset_and_withholds_the_rest(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    recs = _premium_records(reg, pool, A, 4)
    d = selective_disclosure(A, recs, [0, 2])
    assert isinstance(d, DisclosedCredit) and d.complete is True
    assert d.disclosed_count == 2 and d.withheld_count == 2
    assert "issues nothing" in d.reason
    # disclosing nothing is not complete (deny-by-default)
    assert selective_disclosure(A, recs, []).complete is False
    # an out-of-range disclosure index is refused
    with pytest.raises(IncomeRefused):
        selective_disclosure(A, recs, [0, 9])


def test_selective_disclosure_of_a_foreign_record_breaks_it(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    recs = _premium_records(reg, pool, A, 2)
    other = record_premium(pool, B, "b-prem", contribution_class="attested", author=AUTHOR, source_ref="s",
                           at=AT, registry=reg, amount=5.0)
    recs.append({"receipt": other, "work_ref": "b-prem", "contribution_class": "attested", "source": "premium",
                 "amount": 5.0, "extra": {"pool": pool.pool_id}})
    assert selective_disclosure(A, recs, [0, 2]).complete is False   # index 2 is B's, not A's


def _attestors():
    return [{"party": B, "work_ref": "b-attests"}, {"party": C, "work_ref": "c-attests"}]


def test_a_multi_party_attestation_chain_verifies_end_to_end(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    chain = build_attestation_chain(A, pool, "storm-claim", claim_class="attested", attestors=_attestors(),
                                    registry=reg, at=AT, author=AUTHOR, source_ref="s", amount=300.0)
    assert len(chain) == 3
    assert verify_attestation_chain(chain, A, pool, "storm-claim", claim_class="attested",
                                    attestors=_attestors(), amount=300.0) is True


def test_a_reordered_or_short_attestation_chain_fails(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    chain = build_attestation_chain(A, pool, "storm-claim", claim_class="attested", attestors=_attestors(),
                                    registry=reg, at=AT, author=AUTHOR, source_ref="s", amount=300.0)
    reordered = [chain[0], chain[2], chain[1]]          # swap the two attestation links -> positions no longer match
    assert verify_attestation_chain(reordered, A, pool, "storm-claim", claim_class="attested",
                                    attestors=_attestors(), amount=300.0) is False
    assert verify_attestation_chain(chain[:2], A, pool, "storm-claim", claim_class="attested",
                                    attestors=_attestors(), amount=300.0) is False   # wrong length
    assert verify_attestation_chain([], A, pool, "storm-claim", claim_class="attested",
                                    attestors=_attestors(), amount=300.0) is False   # empty


def test_unknown_claim_grade_in_a_chain_is_refused(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    with pytest.raises(IncomeRefused):
        build_attestation_chain(A, pool, "x", claim_class="guessed", attestors=_attestors(), registry=reg,
                                at=AT, author=AUTHOR, source_ref="s")


def test_composes_the_sealed_s11v1_and_s10_floors_only():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "risk"
           / "advanced_pooling.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "zk_proofs",
                    "objects.registry", "objects.identity", "material.", "provision_", ".group_applications"):
            assert tok not in ln, f"advanced_pooling composes S11 V1 + S10 only (no crypto, no V03), not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling
    for ln in sibling:
        assert (".mutual_protection" in ln or ".economy" in ln), \
            f"only the sealed S11 V1 + S10 floors may be composed: {ln}"
