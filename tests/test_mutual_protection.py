# -*- coding: utf-8 -*-
"""Proof-first tests for risk.mutual_protection (S11 Vol 1, the OPENER:
Insurance, Credit & Reputation Without Extraction).

Kill-targets pinned (the 7-part S11 fence + the primitive):
- composes the sealed S10 pool + contribution floors ONLY — invents no new engine, rolls no cryptography;
- a premium is a receipted obligation the member OWNS; verified from a receipt (weakest-party);
- a claim is PROOF-GRADED (attested/computed/hybrid); an unknown grade is refused; a tampered claim flips verify;
- claims SETTLE VIA THE PORT ONLY — settle_claim composes the sealed pool-settlement; no in-node custody;
- THE S11 FENCE — no in-node custody/reserve/netting, no underwriting, no credit issuance, no reputation score
  (RISK_BREACH_FIELDS refused in code);
- credit = PORTABLE RECEIPT HISTORY, never issuance — complete iff every receipt verifies; a foreign one breaks it;
- reputation ≠ token/score authority — a tally of verified receipts, not a score;
- F1 reputation-weighted matching — ranks by count of VERIFIED receipts (transparent), most-proven first;
- weakest-party — a claimant/member verifies from a receipt they hold.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.risk.mutual_protection import (
    form_protection_pool, record_premium, verify_premium, record_claim, verify_claim, settle_claim,
    credit_history, reputation_package, match_by_reputation,
    CreditHistory, ReputationPackage, CLAIM_CLASSES, RISK_BREACH_FIELDS, IncomeRefused, IncomeStatus,
)

A, B, AUTHOR, AT = "ridgeline-kenn", "cedar-partner", "Kenneth Mangum", "2026-08-10T04:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _pool(tmp_path):
    return form_protection_pool("ridgeline-mutual-aid", (A, B)), _reg(tmp_path)


def test_a_protection_pool_holds_no_value_and_needs_two_members(tmp_path):
    pool, _ = _pool(tmp_path)
    assert pool.has(A) and pool.has(B)
    with pytest.raises(IncomeRefused):        # a pool of one protects no one (inherits the sealed pool-fence)
        form_protection_pool("solo", (A,))


def test_a_premium_is_a_receipted_obligation_the_member_owns(tmp_path):
    pool, reg = _pool(tmp_path)
    r = record_premium(pool, A, "aug-premium", contribution_class="attested", author=AUTHOR,
                       source_ref="prem:1", at=AT, registry=reg, amount=25.0)
    assert r["mandate"] == A
    st = verify_premium(r, pool, A, "aug-premium", contribution_class="attested", amount=25.0)
    assert st.provisioned is True


def test_a_claim_is_proof_graded_and_an_unknown_grade_is_refused(tmp_path):
    pool, reg = _pool(tmp_path)
    r = record_claim(A, pool, "storm-damage", claim_class="attested", author=AUTHOR, source_ref="clm:1",
                     at=AT, registry=reg, amount=300.0)
    assert verify_claim(r, A, pool, "storm-damage", claim_class="attested", amount=300.0).provisioned is True
    with pytest.raises(IncomeRefused):
        record_claim(A, pool, "x", claim_class="guessed", author=AUTHOR, source_ref="c", at=AT, registry=reg)
    assert CLAIM_CLASSES == frozenset({"attested", "computed", "hybrid"})


def test_a_tampered_claim_flips_verify(tmp_path):
    pool, reg = _pool(tmp_path)
    r = record_claim(A, pool, "storm-damage", claim_class="attested", author=AUTHOR, source_ref="c", at=AT,
                     registry=reg, amount=300.0)
    assert verify_claim(r, A, pool, "storm-damage", claim_class="computed", amount=300.0).provisioned is False
    assert verify_claim(r, A, pool, "storm-damage", claim_class="attested", amount=999.0).provisioned is False


def test_claims_settle_via_the_port_only_no_in_node_custody(tmp_path):
    pool, reg = _pool(tmp_path)
    s = settle_claim(pool, A, {"share": "300 credits", "port_ref": "PortDirective:pd-claim-1"})
    assert s.pool_id == pool.pool_id and s.directives[0]["member"] == A
    assert s.directives[0]["port_ref"] == "PortDirective:pd-claim-1"
    # a settlement with no Port directive is refused — a claim settles ONLY via the sealed Port
    with pytest.raises(IncomeRefused):
        settle_claim(pool, A, {"share": "300 credits"})


def test_the_s11_fence_refuses_custody_underwriting_issuance_and_score(tmp_path):
    pool, reg = _pool(tmp_path)
    for breach in ("custody", "reserve", "netting", "underwrite", "risk_price", "issue_credit",
                   "credit_limit", "reputation_score", "rating"):
        with pytest.raises(IncomeRefused):
            record_premium(pool, A, "p", contribution_class="attested", author=AUTHOR, source_ref="s", at=AT,
                           registry=reg, extra={breach: True})
        with pytest.raises(IncomeRefused):
            settle_claim(pool, A, {"share": "1", "port_ref": "PortDirective:x", breach: True})
    assert {"underwrite", "issue_credit", "reputation_score", "custody"}.issubset(RISK_BREACH_FIELDS)


def test_credit_is_a_portable_receipt_history_never_issuance(tmp_path):
    pool, reg = _pool(tmp_path)
    recs = []
    for w in ("aug-premium", "sep-premium"):
        r = record_premium(pool, A, w, contribution_class="attested", author=AUTHOR, source_ref="s", at=AT,
                           registry=reg, amount=25.0)
        recs.append({"receipt": r, "work_ref": w, "contribution_class": "attested", "source": "premium",
                     "amount": 25.0, "extra": {"pool": pool.pool_id}})
    h = credit_history(A, recs)
    assert isinstance(h, CreditHistory) and h.complete is True and h.verified_count == 2
    assert "issues nothing" in h.reason
    # a foreign record breaks the history
    other = record_premium(pool, B, "b-prem", contribution_class="attested", author=AUTHOR, source_ref="s",
                           at=AT, registry=reg, amount=10.0)
    recs.append({"receipt": other, "work_ref": "b-prem", "contribution_class": "attested", "source": "premium",
                 "amount": 10.0, "extra": {"pool": pool.pool_id}})
    assert credit_history(A, recs).complete is False
    # a credit-history record carrying an issuance field is refused (the S11 fence)
    with pytest.raises(IncomeRefused):
        credit_history(A, [{"receipt": {}, "work_ref": "x", "contribution_class": "attested",
                            "source": "premium", "issue_credit": True}])


def test_empty_credit_history_is_not_complete(tmp_path):
    assert credit_history(A, []).complete is False


def test_reputation_is_a_tally_of_verified_receipts_not_a_score(tmp_path):
    pool, reg = _pool(tmp_path)
    recs = []
    for w, cls in [("verify-work", "computed"), ("skill-help", "attested"), ("more-help", "attested")]:
        r = record_claim(A, pool, w, claim_class=cls, author=AUTHOR, source_ref="s", at=AT, registry=reg)
        recs.append({"receipt": r, "work_ref": w, "contribution_class": cls, "source": "claim",
                     "amount": None, "extra": {"pool": pool.pool_id, "claim": True}})
    rep = reputation_package(A, recs)
    assert isinstance(rep, ReputationPackage) and rep.reputation_weight == 3 and rep.verified_count == 3
    assert rep.by_class == {"computed": 1, "attested": 2} and "not a score" in rep.reason
    with pytest.raises(IncomeRefused):
        reputation_package(A, [{"receipt": {}, "work_ref": "x", "contribution_class": "attested",
                                "source": "claim", "reputation_score": 900}])


def test_f1_reputation_weighted_matching_ranks_by_verified_receipts(tmp_path):
    pool, reg = _pool(tmp_path)

    def recs_for(party, n):
        out = []
        for i in range(n):
            r = record_claim(party, pool, f"{party}-w{i}", claim_class="attested", author=AUTHOR,
                             source_ref="s", at=AT, registry=reg)
            out.append({"receipt": r, "work_ref": f"{party}-w{i}", "contribution_class": "attested",
                        "source": "claim", "amount": None, "extra": {"pool": pool.pool_id, "claim": True}})
        return out

    ranked = match_by_reputation([{"party": A, "records": recs_for(A, 1)},
                                  {"party": B, "records": recs_for(B, 3)}])
    assert [r["party"] for r in ranked] == [B, A]           # most-proven first
    assert ranked[0]["reputation_weight"] == 3 and ranked[1]["reputation_weight"] == 1


def test_human_primacy_gated_claim_refused_without_approval(tmp_path):
    pool, reg = _pool(tmp_path)
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["record_claim"]}
    with pytest.raises(IncomeRefused):
        record_claim(A, pool, "large-claim", claim_class="attested", author=AUTHOR, source_ref="s", at=AT,
                     registry=reg, gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_composes_the_sealed_s10_floors_only():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "risk"
           / "mutual_protection.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "material.", "provision_"):
            assert tok not in ln, f"mutual_protection composes the sealed S10 floors only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from ..")]
    assert sibling, "must compose the sealed economy floors"
    for ln in sibling:
        assert (".economy.pool" in ln or ".economy.contribution" in ln), \
            f"only the sealed S10 pool + contribution floors may be composed: {ln}"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    pool, reg = _pool(tmp_path)
    r = record_claim(A, pool, "storm", claim_class="attested", author=AUTHOR, source_ref="s", at=AT,
                     registry=reg, amount=50.0)
    st = verify_claim(r, A, pool, "storm", claim_class="attested", amount=50.0)
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
