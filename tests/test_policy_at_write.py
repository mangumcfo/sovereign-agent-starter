"""S4-G1 — policy-at-the-write acceptance tests (spec docs/specs/S4-G1_policy_at_the_write_v0.1.md §8).

Tests are numbered/named to the spec's 10-item acceptance list. The rule fires AT the write (open /
approve / close) or it isn't a rule; its only power is refusal with the rule cited — raised in the
EconomicActionRefused posture AND recorded as a ledger fact (§4, raise-and-record). Test 3 shares
G2's supply-cap fixture (addendum); test 10 proves no-policy-declared behavior is identical.
"""
import json

import pytest

from sovereign_agent.compliance.policy_loader import PolicyLoader, PolicyNotLoadableError
from sovereign_agent.obligations import ObligationLedger
from sovereign_agent.obligations import token_schema as ts
from sovereign_agent.obligations import write_rules as wr

from test_token_schema import E2, GATE, REG, supply_cap_mint_history


def _doc(rules, policy_id="s4_test_governance", version="1.0", **extra):
    return {"id": policy_id, "version": version, "write_rules": rules, **extra}


def _rule(rule_id, predicate_name, applies_to, effect="refuse", message="rule refused this write",
          **args):
    return {"id": rule_id, "applies_to": applies_to,
            "predicate": {"name": predicate_name, **args},
            "effect": effect, "message": message}


SIX_PREDICATE_DOC = _doc([
    _rule("ISSUANCE-2", "amount_ceiling", {"kind": "token.mint"}, max="1000",
          message="mint above ceiling requires charter amendment"),
    _rule("SUPPLY-1", "supply_cap", {"kind": "token.mint"}, cap="100",
          message="supply cap is a charter decision"),
    _rule("TRUTH-1", "require_evidence", {"kind": "release.*"}, floor="E2",
          message="a release closes on verified evidence only"),
    _rule("K1-GATE", "require_gate", {"kind": "treasury.*"}, gate="human",
          message="the human gate is never waived"),
    _rule("CHARTER-F1", "forbid_class", {"classification": "FORBIDDEN"}, **{"class": "FORBIDDEN"},
          message="charter-forbidden class"),
    _rule("K4-1", "threshold_second_approver", {"kind": "token.mint"},
          effect="require_second_approver", above="50",
          message="a mint above the K4 threshold needs a second approver"),
])


def _led(tmp_path, policy, registry=REG, gate=GATE, **kw):
    return ObligationLedger(root=tmp_path, principal_id="node", gate=gate,
                            token_registry=registry, write_policy=policy, **kw)


def _refusals(led, rule_id=None):
    out = [e for e in led.iter_entries() if e.get("type") == "refusal"]
    return [r for r in out if r.get("rule_id") == rule_id] if rule_id else out


# 1. Document with the six v0.1 predicates loads; unknown predicate refuses to load.
def test_1_six_predicates_load_unknown_predicate_refuses():
    policy = wr.load_write_policy(SIX_PREDICATE_DOC)
    assert policy.id == "s4_test_governance" and policy.version == "1.0"
    assert [r.predicate for r in policy.rules] == [
        "amount_ceiling", "supply_cap", "require_evidence",
        "require_gate", "forbid_class", "threshold_second_approver"]
    # unknown predicate ⇒ the DOCUMENT refuses to load (fail-closed at load, not at first use)
    with pytest.raises(wr.WritePolicyLoadError):
        wr.load_write_policy(_doc([_rule("VIBES-1", "vibes_ok", {"kind": "*"}, level="chill")]))
    # malformed args refuse to load
    with pytest.raises(wr.WritePolicyLoadError):
        wr.load_write_policy(_doc([_rule("BAD-ARG", "amount_ceiling", {"kind": "*"}, max="lots")]))
    # empty applies_to refuses to load
    with pytest.raises(wr.WritePolicyLoadError):
        wr.load_write_policy(_doc([_rule("NO-SEL", "amount_ceiling", {}, max="1")]))
    # duplicate rule id refuses to load
    dup = _rule("DUP-1", "amount_ceiling", {"kind": "*"}, max="1")
    with pytest.raises(wr.WritePolicyLoadError):
        wr.load_write_policy(_doc([dup, dict(dup)]))


# 2. amount_ceiling breach at open ⇒ refusal recorded with rule id + version; nothing appended
#    as an obligation.
def test_2_amount_ceiling_breach_at_open_recorded_nothing_appended(tmp_path):
    led = _led(tmp_path, _doc([_rule("ISSUANCE-2", "amount_ceiling", {"kind": "token.mint"},
                                     max="1000", message="mint above ceiling")]))
    with pytest.raises(wr.WriteRefused) as exc_info:
        led.open("mint 5000 QUAD", owner="alice", material=True, kind="token.mint",
                 token={"token_id": "QUAD", "amount": "5000",
                        "dr_account": "issuance_authority", "cr_account": "alice"})
    assert "ISSUANCE-2" in str(exc_info.value)
    refusal = _refusals(led, "ISSUANCE-2")
    assert len(refusal) == 1
    assert refusal[0]["policy_id"] == "s4_test_governance"
    assert refusal[0]["policy_version"] == "1.0"
    assert refusal[0]["write_point"] == "open" and refusal[0]["refused_at"]
    assert not [e for e in led.iter_entries() if e.get("type") == "debit"]   # no obligation appended
    assert led.verify_chain() is True


# 3. supply_cap breach at close of a token.mint ⇒ refused; replay-including-entry math per
#    S4-G2 test 7 (shared fixture) — here the cap is DECLARED IN THE POLICY (the G1 wire).
def test_3_supply_cap_breach_at_close_shared_fixture(tmp_path):
    led = _led(tmp_path,
               _doc([_rule("SUPPLY-1", "supply_cap", {"kind": "token.mint"}, cap="100",
                           message="supply cap is a charter decision")]),
               registry={"QUAD": {"precision": 2}})     # cap lives ONLY in the policy document
    pending = supply_cap_mint_history(led)              # 80 sealed + 40 approved-pending
    with pytest.raises(wr.WriteRefused) as exc_info:
        led.close(pending["id"], evidence=E2)
    assert "SUPPLY-1" in str(exc_info.value) and "120" in str(exc_info.value)
    refusal = _refusals(led, "SUPPLY-1")
    assert len(refusal) == 1 and refusal[0]["write_point"] == "close"
    entries = list(led.iter_entries())
    assert ts.circulating_supply(entries, "QUAD") == 80   # the breach never sealed


# 4. require_evidence: E2 with E1 evidence at close ⇒ refused, rule cited.
def test_4_require_evidence_e2_refuses_e1_close(tmp_path):
    led = _led(tmp_path, _doc([_rule("TRUTH-1", "require_evidence", {"kind": "release.*"},
                                     floor="E2", message="verified evidence only")]))
    ob = led.open("ship release v1.2", kind="release.ship")
    with pytest.raises(wr.WriteRefused) as exc_info:
        led.close(ob["id"], evidence="/artifacts/release_notes.md")          # E1: path, no hash
    assert "TRUTH-1" in str(exc_info.value)
    assert len(_refusals(led, "TRUTH-1")) == 1
    credit = led.close(ob["id"], evidence="/artifacts/release_notes.md hash a1b2c3d4e5f60718")  # E2
    assert credit["type"] == "credit" and credit["evidence_tier"] == "E2"


# 5. threshold_second_approver above threshold: single approve refused; two approvals
#    (distinct principals, proposer excluded) seals.
def test_5_threshold_second_approver_quorum_raise(tmp_path):
    led = _led(tmp_path, _doc([_rule("K4-1", "threshold_second_approver", {"kind": "token.mint"},
                                     effect="require_second_approver", above="50",
                                     message="second approver above 50")]))
    ob = led.open("mint 80 QUAD", owner="alice", material=True, kind="token.mint",
                  token={"token_id": "QUAD", "amount": "80",
                         "dr_account": "issuance_authority", "cr_account": "alice"})
    assert ob["quorum"] == 2 and ob["quorum_source"] == "rule:K4-1"   # the rule set the bar, replayably
    led.approve(ob["id"], approved_by="kenn")            # one reviewer in — floor unmet
    assert led._is_approved(ob["id"]) is False
    with pytest.raises(wr.WriteRefused) as exc_info:
        led.close(ob["id"], evidence=E2)                 # refused WITH THE RULE CITED
    assert "K4-1" in str(exc_info.value)
    led.approve(ob["id"], approved_by="alice")           # the PROPOSER — never counts toward quorum
    assert led._is_approved(ob["id"]) is False
    led.approve(ob["id"], approved_by="gwen")            # second DISTINCT principal ⇒ floor met
    assert led._is_approved(ob["id"]) is True
    assert led.close(ob["id"], evidence=E2)["type"] == "credit"
    # a below-threshold mint keeps the single-approval flow (the bar is amount-aware, K4)
    small = led.open("mint 10 QUAD", owner="alice", material=True, kind="token.mint",
                     token={"token_id": "QUAD", "amount": "10",
                            "dr_account": "issuance_authority", "cr_account": "alice"})
    assert "quorum" not in small


# 6. require_gate: human composes with AH-1 — simulated approval still DENIED path, real gate
#    passes; refusal record shape identical to AH-1's.
def test_6_require_gate_composes_with_ah1(tmp_path):
    policy = _doc([_rule("K1-GATE", "require_gate", {"kind": "treasury.*"}, gate="human",
                         message="the human gate is never waived")])
    # gate-less ledger (no human breath-gate to satisfy) ⇒ the AH-1 DENIED path, exactly as today
    led = _led(tmp_path / "gateless", policy, gate=None)
    ob = led.open("wire treasury funds", owner="alice", material=True, kind="treasury.wire")
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="kenn")
    denied = [e for e in led.iter_entries()
              if e.get("type") == "approval" and e.get("disposition") == "denied"]
    assert len(denied) == 1
    # shape identical to AH-1's on a policy-LESS ledger (the rule adds nothing, waives nothing)
    plain = ObligationLedger(root=tmp_path / "plain", principal_id="node")
    pb = plain.open("wire treasury funds", owner="alice", material=True)
    with pytest.raises(PermissionError):
        plain.approve(pb["id"], approved_by="kenn")
    plain_denied = [e for e in plain.iter_entries()
                    if e.get("type") == "approval" and e.get("disposition") == "denied"][0]
    assert set(denied[0].keys()) == set(plain_denied.keys())
    assert denied[0]["gate"]["status"] == plain_denied["gate"]["status"] == "denied"
    assert denied[0]["gate"]["real"] is False
    # a REAL human gate passes — the rule demands the gate; it cannot waive or replace it
    gated = _led(tmp_path / "gated", policy)
    wire_ob = gated.open("wire treasury funds", owner="alice", material=True, kind="treasury.wire")
    gated.approve(wire_ob["id"], approved_by="kenn")
    assert gated.close(wire_ob["id"], evidence=E2)["type"] == "credit"


# 7. Missing policy document on an enforcement-enabled ledger ⇒ POLICY-0 refusal on material
#    write; placeholder only via allow_placeholder=True and stamps PLACEHOLDER.
def test_7_policy0_loud_fallback_and_placeholder(tmp_path):
    led = _led(tmp_path / "p0", "/nonexistent/governance.yaml")
    with pytest.raises(wr.WriteRefused) as exc_info:
        led.open("material act under broken policy", material=True)
    assert "POLICY-0" in str(exc_info.value)
    refusal = _refusals(led, "POLICY-0")
    assert len(refusal) == 1
    assert refusal[0]["message"].startswith("policy declared but not loadable")
    nm = led.open("non-material note", material=False)          # §5: MATERIAL writes refuse
    assert nm["type"] == "debit"
    # dev harness: explicit allow_placeholder=True ⇒ blessed entries stamped PLACEHOLDER, visibly
    dev = _led(tmp_path / "dev", "/nonexistent/governance.yaml", allow_placeholder=True)
    ob = dev.open("material act under placeholder", material=True)
    assert ob["policy_version"] == "PLACEHOLDER"
    approval = dev.approve(ob["id"], approved_by="kenn")
    assert approval["policy_version"] == "PLACEHOLDER"
    credit = dev.close(ob["id"], evidence=E2)
    assert credit["policy_version"] == "PLACEHOLDER"
    # the PolicyLoader placeholder is retired the same way (§5): loud by default, opt-in stamped
    loader = PolicyLoader(primary_source=tmp_path / "nowhere", secondary_source=tmp_path / "nowhere")
    with pytest.raises(PolicyNotLoadableError):
        loader.load_policy("missing_policy_xyz")
    placeholder = loader.load_policy("missing_policy_xyz", allow_placeholder=True)
    assert placeholder.version == "PLACEHOLDER"


# 8. policy.amend flow: new version effective only after seal; pre-amendment entries replay
#    under the old version (as-of correctness).
def test_8_policy_amend_as_of_correctness(tmp_path):
    v1 = _doc([_rule("GRANT-1", "amount_ceiling", {"kind": "grant.*"}, max="100",
                     message="grants above 100 need a charter amendment")], version="1.0")
    v2 = _doc([_rule("GRANT-1", "amount_ceiling", {"kind": "grant.*"}, max="1000",
                     message="grants above 1000 need a charter amendment")], version="2.0")
    led = _led(tmp_path, v1)

    def open_grant(amount):
        return led.open(f"grant {amount}", owner="alice", material=True,
                        kind="grant.award", lgp={"economic_value": amount})

    with pytest.raises(wr.WriteRefused):
        open_grant("150")                                       # v1.0 in force ⇒ refused
    assert _refusals(led, "GRANT-1")[0]["policy_version"] == "1.0"
    # the amendment is a MATERIAL obligation: E2 evidence (the new document's hash) + human gate
    amend = led.open("amend governance to v2.0", owner="alice", material=True,
                     kind="policy.amend", policy_amendment={"document": v2})
    led.approve(amend["id"], approved_by="kenn")
    with pytest.raises(wr.WriteRefused):
        open_grant("150")                                       # approved-but-UNSEALED amends nothing
    doc_hash = wr.document_sha256(v2)
    with pytest.raises(ValueError):
        led.close(amend["id"], evidence="/policies/governance_v2.yaml")   # E1 cannot seal an amendment
    led.close(amend["id"], evidence=f"/policies/governance_v2.yaml sha256:{doc_hash}")  # E2 seals
    assert open_grant("150")["type"] == "debit"                 # v2.0 now in force
    with pytest.raises(wr.WriteRefused):
        open_grant("5000")                                      # v2.0 ceiling still binds
    refusals = _refusals(led, "GRANT-1")
    versions = [r["policy_version"] for r in refusals]
    assert versions == ["1.0", "1.0", "2.0"]                    # each 'no' cites the version IN FORCE
    # a FRESH instance over the same chain re-derives the same active version (replay, not state)
    led2 = _led(tmp_path, v1)
    with pytest.raises(wr.WriteRefused):
        led2.open("grant 5000", owner="alice", material=True, kind="grant.award",
                  lgp={"economic_value": "5000"})
    assert _refusals(led2, "GRANT-1")[-1]["policy_version"] == "2.0"


# 9. Refusal records survive replay byte-identically; chain verify stays green.
def test_9_refusal_records_survive_replay_byte_identically(tmp_path):
    led = _led(tmp_path, _doc([_rule("ISSUANCE-2", "amount_ceiling", {"kind": "token.mint"},
                                     max="1000", message="mint above ceiling")]))
    for amount in ("5000", "2000"):
        with pytest.raises(wr.WriteRefused):
            led.open(f"mint {amount}", owner="alice", material=True, kind="token.mint",
                     token={"token_id": "QUAD", "amount": amount,
                            "dr_account": "issuance_authority", "cr_account": "alice"})

    def refusal_bytes(ledger):
        return json.dumps([e for e in ledger.iter_entries() if e.get("type") == "refusal"],
                          sort_keys=True)

    first = refusal_bytes(led)
    fresh = ObligationLedger(root=tmp_path, principal_id="node")   # replays the same chain from disk
    assert refusal_bytes(fresh) == first                           # byte-identical
    assert fresh.verify_chain() is True and led.verify_chain() is True
    assert len(_refusals(led)) == 2


# 10. Existing test suite stays green with no policy declared (no behavior change by default) —
#     the suite-level proof is the full pytest run recorded in the build notes; this test pins the
#     contract: a ledger with NO policy declared behaves identically, entry for entry.
def test_10_no_policy_declared_identical_behavior(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", gate=GATE)   # constructed as today
    assert led.write_policy_declared is False
    ob = led.open("material promote", owner="alice", material=True)
    approval = led.approve(ob["id"], approved_by="kenn")
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    nm = led.open("routine note", material=False)
    nm_credit = led.close(nm["id"], evidence="~/proof.json")
    # exactly the pre-S4 entry shapes — no policy stamp, no refusal lane, no token fields
    assert set(ob.keys()) == {"type", "id", "title", "owner", "principal_id", "classification",
                              "intent", "ref", "material", "draft", "approved", "approved_by",
                              "approved_at", "timestamp", "prev_hash", "hash"}
    assert set(approval.keys()) == {"type", "id", "approves", "approved_by", "disposition",
                                    "gate", "principal_id", "timestamp", "prev_hash", "hash"}
    assert set(credit.keys()) == set(nm_credit.keys()) == {
        "type", "id", "closes", "evidence", "evidence_tier", "closed_by", "principal_id",
        "receipt", "timestamp", "prev_hash", "hash"}
    assert not [e for e in led.iter_entries() if e.get("type") == "refusal"]
    assert led.verify_chain() is True
    assert led.by_status() == {"open": 0, "closed": 2, "total": 2}
