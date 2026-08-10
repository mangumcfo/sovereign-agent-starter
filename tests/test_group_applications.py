# -*- coding: utf-8 -*-
"""Proof-first tests for risk.group_applications (S11 Vol 3, Industry, Group & Affinity Applications).

Kill-targets pinned:
- composes the sealed S11 V1 (mutual_protection) + S10 floors ONLY — NOT the advanced-mechanics volume (S11 V2);
- a group pool is formed of a chosen kind (professional/affinity/enterprise/cooperative/family/network); an
  unknown kind is refused;
- a group premium / group claim is the member's OWN receipted/proof-graded record; a claim settles via the Port;
- group_reputation aggregates members' VERIFIED receipts into a transparent group standing, NOT a score; a
  member whose records do not verify does not inflate the group;
- cross_entity_match ranks entities by verified reputation (most-proven first) — shared visibility, no shared control;
- the S11 fence is inherited (an extraction field is refused); weakest-party plain bool.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.risk.group_applications import (
    form_group_pool, group_premium, verify_group_premium, group_claim, group_reputation, cross_entity_match,
    GroupReputation, GROUP_CLASSES, RISK_BREACH_FIELDS, IncomeRefused, IncomeStatus,
)
from sovereign_agent.risk.mutual_protection import verify_claim

A, B, C, AUTHOR, AT = "ridgeline-kenn", "cedar-partner", "granite-neighbor", "Kenneth Mangum", "2026-08-10T06:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_form_group_pool_by_kind_and_unknown_kind_refused(tmp_path):
    pool = form_group_pool("welders-guild", (A, B), group_class="professional")
    assert pool.has(A) and pool.has(B)
    with pytest.raises(IncomeRefused):
        form_group_pool("x", (A, B), group_class="guessed")
    assert GROUP_CLASSES == frozenset({"professional", "affinity", "enterprise", "cooperative", "family", "network"})


def test_a_group_premium_is_the_members_own_receipted_obligation(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("welders-guild", (A, B), group_class="professional")
    r = group_premium(pool, A, "guild-dues", group_class="professional", contribution_class="attested",
                      author=AUTHOR, source_ref="s", at=AT, registry=reg, amount=50.0)
    assert r["mandate"] == A
    st = verify_group_premium(r, pool, A, "guild-dues", group_class="professional",
                              contribution_class="attested", amount=50.0)
    assert st.provisioned is True


def test_a_group_claim_is_proof_graded_and_owned_and_settles_via_port(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("coop", (A, B), group_class="cooperative")
    r = group_claim(A, pool, "equipment-loss", group_class="cooperative", claim_class="attested", author=AUTHOR,
                    source_ref="s", at=AT, registry=reg, amount=400.0)
    assert verify_claim(r, A, pool, "equipment-loss", claim_class="attested", amount=400.0,
                        extra={"group_class": "cooperative"}).provisioned is True
    with pytest.raises(IncomeRefused):
        group_claim(A, pool, "x", group_class="cooperative", claim_class="guessed", author=AUTHOR,
                    source_ref="s", at=AT, registry=reg)


def test_the_s11_fence_is_inherited_on_group_records(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("coop", (A, B), group_class="cooperative")
    for breach in ("custody", "underwrite", "issue_credit", "reputation_score"):
        with pytest.raises(IncomeRefused):
            group_premium(pool, A, "p", group_class="cooperative", contribution_class="attested", author=AUTHOR,
                          source_ref="s", at=AT, registry=reg, extra={breach: True})
    assert {"underwrite", "issue_credit", "reputation_score"}.issubset(RISK_BREACH_FIELDS)


def _member_records(reg, pool, party, n, gc="professional"):
    recs = []
    for i in range(n):
        r = group_premium(pool, party, f"{party}-d{i}", group_class=gc, contribution_class="attested",
                          author=AUTHOR, source_ref="s", at=AT, registry=reg, amount=10.0)
        recs.append({"receipt": r, "work_ref": f"{party}-d{i}", "contribution_class": "attested",
                     "source": "premium", "amount": 10.0, "extra": {"pool": pool.pool_id, "group_class": gc}})
    return recs


def test_group_reputation_aggregates_verified_receipts_not_a_score(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("welders-guild", (A, B), group_class="professional")
    entries = [{"party": A, "records": _member_records(reg, pool, A, 2)},
               {"party": B, "records": _member_records(reg, pool, B, 3)}]
    gr = group_reputation("welders-guild", entries)
    assert isinstance(gr, GroupReputation) and gr.group_weight == 5 and gr.member_count == 2
    assert gr.by_class == {"attested": 5} and "not a score" in gr.reason


def test_a_member_whose_records_do_not_verify_does_not_inflate_the_group(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("welders-guild", (A, B), group_class="professional")
    good = _member_records(reg, pool, A, 2)
    # a fabricated record for B (wrong owner on A's receipt) does not verify -> contributes 0
    forged = [{"receipt": good[0]["receipt"], "work_ref": good[0]["work_ref"], "contribution_class": "attested",
               "source": "premium", "amount": 10.0, "extra": {"pool": pool.pool_id, "group_class": "professional"}}]
    gr = group_reputation("welders-guild", [{"party": A, "records": good},
                                            {"party": B, "records": forged}])
    assert gr.group_weight == 2 and gr.member_count == 2   # B's forged record verifies as A's, not B's -> 0


def test_cross_entity_match_ranks_by_verified_reputation(tmp_path):
    reg = _reg(tmp_path)
    p1 = form_group_pool("guild-a", (A, B), group_class="professional")
    p2 = form_group_pool("guild-b", (B, C), group_class="affinity")
    ranked = cross_entity_match([
        {"entity": "guild-a", "member_records": [{"party": A, "records": _member_records(reg, p1, A, 1)}]},
        {"entity": "guild-b", "member_records": [{"party": C, "records": _member_records(reg, p2, C, 3, gc="affinity")}]},
    ])
    assert [r["entity"] for r in ranked] == ["guild-b", "guild-a"]
    assert ranked[0]["reputation_weight"] == 3 and ranked[1]["reputation_weight"] == 1


def test_composes_the_sealed_s11v1_and_s10_floors_only_not_v2():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "risk"
           / "group_applications.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "zk_proofs",
                    "objects.registry", "objects.identity", "material.", "provision_", ".advanced_pooling"):
            assert tok not in ln, f"group_applications composes S11 V1 + S10 only (NOT V2/advanced_pooling), not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling
    for ln in sibling:
        assert (".mutual_protection" in ln or ".economy" in ln), \
            f"only the sealed S11 V1 + S10 floors may be composed: {ln}"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    reg = _reg(tmp_path)
    pool = form_group_pool("coop", (A, B), group_class="cooperative")
    r = group_claim(A, pool, "loss", group_class="cooperative", claim_class="attested", author=AUTHOR,
                    source_ref="s", at=AT, registry=reg, amount=100.0)
    st = verify_claim(r, A, pool, "loss", claim_class="attested", amount=100.0, extra={"group_class": "cooperative"})
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
