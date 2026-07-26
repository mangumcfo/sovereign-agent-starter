"""S4-G2 — token-typed schema acceptance tests (spec docs/specs/S4-G2_token_typed_schema_v0.1.md §6).

Tests are numbered/named to the spec's 10-item acceptance list. A token event is a B32 obligation
with token legs on the EXISTING chain — same seal, same hash-chain, same AH-1 gate, same replay.
Both G2 and G1 are opt-in: a ledger constructed as before behaves byte-identically (test 10).
"""
import json

import pytest

from sovereign_agent.obligations import ObligationLedger
from sovereign_agent.obligations import projection as _proj
from sovereign_agent.obligations import token_schema as ts

# Real human breath-gate stand-in (matches the test_quorum.py idiom: real=True disposition).
GATE = lambda action, ob: {"status": "approved", "real": True, "approver": ob.get("approved_by")}

# Operator-DECLARED token registry (never constants in src): 2-decimal QUAD with a 1000 supply cap.
REG = {"QUAD": {"precision": 2, "supply_cap": "1000"}}

E2 = "/artifacts/token_event.json hash a1b2c3d4e5f60718"   # path + hash => E2
E1 = "/artifacts/token_event.json"                          # path only  => E1


def _led(tmp_path, registry=REG, **kw):
    return ObligationLedger(root=tmp_path, principal_id="node", gate=GATE,
                            token_registry=registry, **kw)


def _event(led, kind, token, approver="kenn", evidence=E2, close=True, owner="alice"):
    """Open -> approve (real gate, approver != owner) -> close one token event. Returns the debit."""
    ob = led.open(f"{kind} {token.get('amount', '')} {token['token_id']}", owner=owner,
                  material=True, kind=kind, token=token)
    led.approve(ob["id"], approved_by=approver)
    if close:
        led.close(ob["id"], evidence=evidence)
    return ob


def _mint(led, amount, holder="alice", close=True, approver="kenn"):
    return _event(led, "token.mint",
                  {"token_id": "QUAD", "amount": amount,
                   "dr_account": "issuance_authority", "cr_account": holder},
                  close=close, approver=approver)


def _transfer(led, amount, sender="alice", receiver="bob", close=True, evidence=E1):
    return _event(led, "token.transfer",
                  {"token_id": "QUAD", "amount": amount,
                   "dr_account": sender, "cr_account": receiver},
                  close=close, evidence=evidence)


def _burn(led, amount, holder="bob", close=True):
    return _event(led, "token.redeem.burn",
                  {"token_id": "QUAD", "amount": amount,
                   "dr_account": holder, "cr_account": "supply_retirement"}, close=close)


def supply_cap_mint_history(led):
    """The shared supply-cap fixture (G2 test 7 / G1 test 3 per the addendum): 80 QUAD sealed in
    circulation, then a 40-QUAD mint opened AND approved — so only close() stands between it and a
    cap breach. Returns the pending mint's debit."""
    _mint(led, "80")
    return _mint(led, "40", close=False)


# 1. mint→transfer→burn round-trip: balances and supply replay correctly; IA/SR identity holds.
def test_1_mint_transfer_burn_round_trip(tmp_path):
    led = _led(tmp_path)
    _mint(led, "100")
    _transfer(led, "30")
    _burn(led, "20")
    entries = list(led.iter_entries())
    assert ts.balance(entries, "QUAD", "alice") == 70
    assert ts.balance(entries, "QUAD", "bob") == 10
    assert ts.balance(entries, "QUAD", ts.IA_ACCOUNT) == -100   # contra: negative-or-zero
    assert ts.balance(entries, "QUAD", ts.SR_ACCOUNT) == 20
    # circulating_supply computes BOTH forms (Σ holders and −IA−SR) and requires agreement (§3).
    assert ts.circulating_supply(entries, "QUAD") == 80
    assert led.verify_chain() is True


# 2. Unbalanced/foreign-leg token entry refused at open with reason.
def test_2_unbalanced_or_foreign_leg_refused_at_open(tmp_path):
    led = _led(tmp_path)
    bad_opens = [
        # mint sourced from a holder, not issuance_authority (foreign dr leg)
        ("token.mint", {"token_id": "QUAD", "amount": "10",
                        "dr_account": "alice", "cr_account": "bob"}),
        # transfer credited INTO the burn sink (foreign cr leg — burn is a kind, never a flag)
        ("token.transfer", {"token_id": "QUAD", "amount": "10",
                            "dr_account": "alice", "cr_account": "supply_retirement"}),
        # self-leg (dr == cr)
        ("token.transfer", {"token_id": "QUAD", "amount": "10",
                            "dr_account": "alice", "cr_account": "alice"}),
        # unbalanced: a missing leg
        ("token.mint", {"token_id": "QUAD", "amount": "10",
                        "dr_account": "issuance_authority"}),
        # no mutation kind exists (§1: no token.adjust, no balance-set)
        ("token.adjust", {"token_id": "QUAD", "amount": "10",
                          "dr_account": "alice", "cr_account": "bob"}),
        # unregistered token_id (rule TOKEN-1)
        ("token.mint", {"token_id": "FAKECOIN", "amount": "10",
                        "dr_account": "issuance_authority", "cr_account": "alice"}),
    ]
    for kind, token in bad_opens:
        with pytest.raises(PermissionError) as exc_info:
            led.open("bad token event", owner="alice", material=True, kind=kind, token=token)
        assert str(exc_info.value)   # refusal carries a reason, never a silent drop
    entries = list(led.iter_entries())
    assert not [e for e in entries if e.get("type") == "debit"]   # nothing appended as an obligation
    # each refusal is a recorded ledger fact in the S4-G1 §4 shape (G2 addendum)
    refusals = [e for e in entries if e.get("type") == "refusal"]
    assert len(refusals) == len(bad_opens)
    assert any(r["rule_id"] == "TOKEN-1" for r in refusals)       # unregistered id, rule cited
    assert all(r["write_point"] == "open" and r["message"] for r in refusals)
    assert led.verify_chain() is True


# 3. Mint without real human gate → DENIED recorded (AH-1 path), never sealed.
def test_3_mint_without_real_gate_denied_recorded_never_sealed(tmp_path):
    led = ObligationLedger(root=tmp_path, principal_id="node", token_registry=REG)  # gate-less
    ob = led.open("mint 50 QUAD", owner="alice", material=True, kind="token.mint",
                  token={"token_id": "QUAD", "amount": "50",
                         "dr_account": "issuance_authority", "cr_account": "alice"})
    with pytest.raises(PermissionError):
        led.approve(ob["id"], approved_by="kenn")     # gate-less + material ⇒ AH-1 DENIED
    entries = list(led.iter_entries())
    assert any(e.get("type") == "approval" and e.get("disposition") == "denied"
               and e.get("approves") == ob["id"] for e in entries)   # the DENIED is recorded
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence=E2)              # never sealed
    entries = list(led.iter_entries())
    assert ts.circulating_supply(entries, "QUAD") == 0   # open/refused entries count 0
    assert led.verify_chain() is True


# 4. Transfer with E0 evidence refused at close (`require_e1` path).
def test_4_transfer_e0_evidence_refused_at_close(tmp_path):
    led = _led(tmp_path)
    _mint(led, "100")
    ob = _transfer(led, "30", close=False)
    with pytest.raises(ValueError):                    # the existing require_e1 path (default True)
        led.close(ob["id"], evidence="done, trust me")
    # and the G2 §1 E1 floor holds even if a caller tries to duck require_e1 (fail-closed)
    with pytest.raises(PermissionError):
        led.close(ob["id"], evidence="done, trust me", require_e1=False)
    entries = list(led.iter_entries())
    assert ts.balance(entries, "QUAD", "bob") == 0     # nothing moved
    assert ts.circulating_supply(entries, "QUAD") == 100


# 5. token.redeem.burn vs .return land in SR vs IA respectively; supply reflects burn only.
def test_5_burn_vs_return_by_target_account(tmp_path):
    led = _led(tmp_path)
    _mint(led, "100")
    _event(led, "token.redeem.return",
           {"token_id": "QUAD", "amount": "30",
            "dr_account": "alice", "cr_account": "issuance_authority"})
    _event(led, "token.redeem.burn",
           {"token_id": "QUAD", "amount": "20",
            "dr_account": "alice", "cr_account": "supply_retirement"})
    entries = list(led.iter_entries())
    assert ts.balance(entries, "QUAD", ts.IA_ACCOUNT) == -70    # return went BACK to the contra source
    assert ts.balance(entries, "QUAD", ts.SR_ACCOUNT) == 20     # ONLY the burn landed in the sink
    assert ts.balance(entries, "QUAD", "alice") == 50
    assert ts.circulating_supply(entries, "QUAD") == 50
    # permanently-retired supply = the burn amount only (the SR sink), never the returned amount
    assert ts.balance(entries, "QUAD", ts.SR_ACCOUNT) == 20


# 6. Checkpoint seals; tampered checkpoint → loud drift breach on verify.
def test_6_checkpoint_seals_and_tampered_checkpoint_breaches_loud(tmp_path):
    led = _led(tmp_path)
    _mint(led, "100")
    _transfer(led, "30")
    entries = list(led.iter_entries())
    good_block = ts.checkpoint_block(entries, "QUAD")
    good = _event(led, "token.checkpoint", good_block)          # E2, material-gated, seals
    assert ts.verify_checkpoint(list(led.iter_entries()), good["id"])["ok"] is True
    # a DRIFTED checkpoint (claims a balance replay does not produce) seals shape-valid…
    bad_block = dict(good_block, balances=dict(good_block["balances"], alice="999"))
    bad = _event(led, "token.checkpoint", bad_block)
    # …but cannot quietly stand: verification recomputes from genesis and names the drift, loud.
    with pytest.raises(ts.TokenIntegrityBreach) as exc_info:
        ts.verify_checkpoint(list(led.iter_entries()), bad["id"])
    assert "DRIFT" in str(exc_info.value).upper()


# 7. Supply-cap breach at close refused, rule cited (registry-declared cap in the token validator;
#    the S4-G1 policy-rule wire for the same math is G1 acceptance test 3 — shared fixture).
def test_7_supply_cap_breach_refused_at_close_rule_cited(tmp_path):
    led = _led(tmp_path, registry={"QUAD": {"precision": 2, "supply_cap": "100"}})
    pending = supply_cap_mint_history(led)     # 80 sealed + 40 approved-pending ⇒ close would hit 120
    with pytest.raises(PermissionError) as exc_info:
        led.close(pending["id"], evidence=E2)
    assert "TOKEN-CAP" in str(exc_info.value)                  # rule cited
    assert "120" in str(exc_info.value) and "100" in str(exc_info.value)
    entries = list(led.iter_entries())
    refusal = [e for e in entries if e.get("type") == "refusal" and e.get("rule_id") == "TOKEN-CAP"]
    assert len(refusal) == 1 and refusal[0]["write_point"] == "close"   # the 'no' is a ledger fact
    assert ts.circulating_supply(entries, "QUAD") == 80        # replay: the breach never sealed
    assert not _proj.is_closed(entries, pending["id"])         # obligation left open, fail-closed


# 8. Amount precision overflow / negative / zero → refused at open.
def test_8_amount_precision_negative_zero_refused_at_open(tmp_path):
    led = _led(tmp_path)   # QUAD precision 2
    for bad_amount in ("1.234", "-5", "0", "abc", "NaN", "Infinity"):
        with pytest.raises(PermissionError):
            led.open("bad amount", owner="alice", material=True, kind="token.mint",
                     token={"token_id": "QUAD", "amount": bad_amount,
                            "dr_account": "issuance_authority", "cr_account": "alice"})
    assert not [e for e in led.iter_entries() if e.get("type") == "debit"]
    # a float amount is refused too (Decimal-exact math only — no float near an amount, ever)
    with pytest.raises(PermissionError):
        led.open("float amount", owner="alice", material=True, kind="token.mint",
                 token={"token_id": "QUAD", "amount": 1.5,
                        "dr_account": "issuance_authority", "cr_account": "alice"})


# 9. Replay determinism: byte-identical balance map across two replays.
def test_9_replay_determinism_byte_identical(tmp_path):
    led = _led(tmp_path)
    _mint(led, "100")
    _transfer(led, "30")
    _burn(led, "20")

    def snapshot(ledger):
        entries = list(ledger.iter_entries())
        return json.dumps({k: str(v) for k, v in ts.balances(entries, "QUAD").items()},
                          sort_keys=True)

    first = snapshot(led)
    second = snapshot(led)                                     # same instance, second fold
    fresh = ObligationLedger(root=tmp_path, principal_id="node", token_registry=REG)
    third = snapshot(fresh)                                    # fresh instance, replay from disk
    assert first == second == third                            # byte-identical


# 10. Existing test suite stays green (no schema break) — the suite-level proof is the full pytest
#     run recorded in the build notes; this test pins the contract programmatically: a ledger
#     constructed as before never emits token/policy fields and behaves exactly as today.
def test_10_no_schema_break_for_legacy_ledgers(tmp_path):
    led = ObligationLedger(root=tmp_path, gate=GATE)           # no registry, no policy — as today
    ob = led.open("legacy material obligation", material=True)
    led.approve(ob["id"], approved_by="owner")
    credit = led.close(ob["id"], evidence="/repo/x.py hash a1b2c3d4e5f60718")
    entries = list(led.iter_entries())
    for e in entries:
        assert "kind" not in e and "token" not in e            # G2 fields never appear unbidden
        assert "policy_version" not in e and e.get("type") != "refusal"   # G1 fields neither
    assert "rejected" not in credit                            # additive stamp absent on executions
    assert led.verify_chain() is True
    assert led.by_status() == {"open": 0, "closed": 1, "total": 1}
