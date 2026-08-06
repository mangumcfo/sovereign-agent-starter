"""Acceptance tests for The Sovereign Port (s6_07, S6 Vol 7) — a governed boundary crossing between the sovereign core
and the outside world. A crossing is the node's own governed object, sanctioned DENY-BY-DEFAULT by a node-declared
boundary rule + a named human, and RECEIPTED — value/data moves through the external rail, never held by the Port. No
central settlement authority, no custody of value, no hub that owns the crossing. Composes the sealed object registry +
Federation Node Governance authorize_crossing + Compliance HumanApprovalGate. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.port.crossing import open_crossing, sanction_crossing, CrossingError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _open(reg, node="nodeA", target="bank-rail", instr=None):
    return open_crossing(reg, node, target, instr or {"pay": "invoice://123", "to": "acct-external"},
                         mandate=node, author=node, source_ref=f"crossing://{node}/1", at="2026-08-06")


def _rule(node="nodeA", target="bank-rail", boundary="external:bank"):
    # the node DECLARES the boundary crossing: this crossing object may be reached by exactly the boundary mandate
    return [SharingRule(f"crossing:{node}:{target}", boundary, "write")]


# ── Ch2 · the governed crossing / adapter (open_crossing) ──────────────────────────────────────────────
def test_open_crossing_registers_a_governed_object(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg)
    assert c["version_hash"]
    assert c["object_id"] == "crossing:nodeA:bank-rail"
    assert c["payload"]["pay"] == "invoice://123"


def test_open_crossing_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(CrossingError):
        open_crossing(reg, "", "bank-rail", {"pay": "x"}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    with pytest.raises(CrossingError):
        open_crossing(reg, "nodeA", "", {"pay": "x"}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    with pytest.raises(CrossingError):
        open_crossing(reg, "nodeA", "bank-rail", {}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")


# ── Ch3 · bank / cash / treasury rails as a governed crossing ──────────────────────────────────────────
def test_bank_rail_crossing_is_sanctioned_and_receipted(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg, target="bank-rail")
    res = sanction_crossing(reg, c, rules=_rule(target="bank-rail"), boundary_mandate="external:bank",
                            approver="treasurer", approval_ref="payment run #7")
    assert res["crossed"] is True
    assert res["boundary"] == "external:bank"
    assert res["crossing_root"] == c["version_hash"]


# ── Ch4 · payment / settlement — the RECEIPT, never the value (no custody) ─────────────────────────────
def test_sanction_crossing_receipts_the_crossing_not_the_value(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg, target="pay-rail", instr={"settle": "po://88", "amount_ref": "external-ledger://88"})
    res = sanction_crossing(reg, c, rules=_rule(target="pay-rail"), boundary_mandate="external:bank",
                            approver="controller", approval_ref="settlement authorization #12")
    # the Port records THAT a sanctioned crossing occurred -- it never holds/moves the value itself
    assert res["crossed"] is True and res["approver"] == "controller"
    for k in ("value", "amount", "funds", "balance", "held"):
        assert k not in res, f"the Port must not custody value (found {k!r} in the receipt)"


def test_sanction_crossing_refuses_undeclared_boundary(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg, target="bank-rail")
    with pytest.raises(CrossingError):
        sanction_crossing(reg, c, rules=[], boundary_mandate="external:bank",
                          approver="treasurer", approval_ref="run #7")  # no declared rule -> deny-by-default


def test_sanction_crossing_refuses_unnamed_approver_or_ref(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg, target="bank-rail")
    with pytest.raises(CrossingError):
        sanction_crossing(reg, c, rules=_rule(), boundary_mandate="external:bank", approver="  ", approval_ref="r")
    with pytest.raises(CrossingError):
        sanction_crossing(reg, c, rules=_rule(), boundary_mandate="external:bank", approver="treasurer", approval_ref="")


def test_sanction_crossing_refuses_nonexistent_crossing(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(CrossingError):
        sanction_crossing(reg, {}, rules=_rule(), boundary_mandate="external:bank",
                          approver="treasurer", approval_ref="run #7")


# ── Ch6 · inbound protocol / EDI / IoT ingestion as a governed crossing ────────────────────────────────
def test_inbound_ingestion_crossing(tmp_path):
    reg = _reg(tmp_path)
    c = _open(reg, target="edi-partner", instr={"pull": "asn://edi/555", "kind": "inbound-ingestion"})
    res = sanction_crossing(reg, c, rules=_rule(target="edi-partner", boundary="external:edi"),
                            boundary_mandate="external:edi", approver="ops-lead", approval_ref="ingestion approval #3")
    assert res["crossed"] is True
    assert res["object_id"] == "crossing:nodeA:edi-partner"
