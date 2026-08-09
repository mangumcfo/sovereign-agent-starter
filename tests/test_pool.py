# -*- coding: utf-8 -*-
"""Proof-first tests for economy.pool (S10 Vol 2, Networked Value Pools Without Extraction).

Kill-targets pinned: composes-contribution.py-only · a pooled contribution is the MEMBER's own · settle ONLY
via the Port (no in-node pool balance / netting / internal settlement — the elevated S10 V2 fence) · no
central pool custodian (deny-by-default on non-members) · weakest-party (member verifies from the receipt).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.pool import (
    form_pool, contribute_to_pool, pool_settlement, verify_pool_contribution,
    Pool, PoolSettlement, POOL_BREACH_FIELDS, IncomeRefused,
)

AUTHOR, AT = "Kenneth Mangum", "2026-08-09T01:00:00Z"
MEMBERS = ["ridgeline-kenn", "cedar-partner"]


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_form_pool_needs_at_least_two_members():
    p = form_pool("ridge-circle", MEMBERS)
    assert isinstance(p, Pool) and p.members == ("ridgeline-kenn", "cedar-partner")
    with pytest.raises(IncomeRefused):
        form_pool("solo", ["ridgeline-kenn"])            # a pool of one is a solo livelihood
    with pytest.raises(IncomeRefused):
        form_pool("", MEMBERS)


def test_pooled_contribution_is_the_members_own(tmp_path):
    p = form_pool("ridge-circle", MEMBERS)
    r = contribute_to_pool(p, "ridgeline-kenn", "skill_service", "weld-job", contribution_class="attested",
                           author=AUTHOR, source_ref="a", at=AT, registry=_reg(tmp_path))
    assert r["kind"] == "income" and r["mandate"] == "ridgeline-kenn"   # the member owns it
    assert r["payload"]["pool"] == "ridge-circle"
    st = verify_pool_contribution(r, p, "ridgeline-kenn", "skill_service", "weld-job",
                                  contribution_class="attested")
    assert st.provisioned is True


def test_a_non_member_cannot_contribute(tmp_path):
    p = form_pool("ridge-circle", MEMBERS)
    with pytest.raises(IncomeRefused):
        contribute_to_pool(p, "stranger", "skill_service", "job", contribution_class="attested",
                           author=AUTHOR, source_ref="a", at=AT, registry=_reg(tmp_path))


def test_pool_settles_only_via_the_port():
    p = form_pool("ridge-circle", MEMBERS)
    s = pool_settlement(p, [("ridgeline-kenn", {"port_ref": "port:ext-1", "share": "60"}),
                            ("cedar-partner", {"port_ref": "port:ext-2", "share": "40"})])
    assert isinstance(s, PoolSettlement)
    assert all("port_ref" in d and d["port_ref"].startswith("port:") for d in s.directives)
    # a member share with NO Port directive is refused — the node cannot settle in-node
    with pytest.raises(IncomeRefused):
        pool_settlement(p, [("ridgeline-kenn", {"share": "100"})])


def test_no_in_node_pool_balance_or_netting():
    p = form_pool("ridge-circle", MEMBERS)
    # a settlement carrying an in-node pool-value field is refused (no pool balance / netting / internal settlement)
    for breach in ("pool_balance", "netting", "internal_settlement"):
        with pytest.raises(IncomeRefused):
            pool_settlement(p, [("ridgeline-kenn", {"port_ref": "port:x", "share": "1", breach: 999})])
    # sanity: the breach fields are the ones the fence guards
    assert {"pool_balance", "netting", "internal_settlement"}.issubset(POOL_BREACH_FIELDS)


def test_cannot_settle_to_a_non_member():
    p = form_pool("ridge-circle", MEMBERS)
    with pytest.raises(IncomeRefused):
        pool_settlement(p, [("stranger", {"port_ref": "port:x", "share": "1"})])


def test_tampered_pool_flips_verify(tmp_path):
    p = form_pool("ridge-circle", MEMBERS)
    other = form_pool("other-circle", MEMBERS)
    r = contribute_to_pool(p, "ridgeline-kenn", "skill_service", "weld-job", contribution_class="attested",
                           author=AUTHOR, source_ref="a", at=AT, registry=_reg(tmp_path))
    # verifying against a DIFFERENT pool must fail (the pool tag is part of the record)
    assert verify_pool_contribution(r, other, "ridgeline-kenn", "skill_service", "weld-job",
                                    contribution_class="attested").provisioned is False


def test_composes_contribution_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "pool.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "provision_", "material.", ".income", ".pool"):
            assert tok not in ln, f"pool must compose contribution.py only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".contribution" in ln for ln in sibling), "the only sibling import is contribution (S10 V1)"
