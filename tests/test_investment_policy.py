"""Investment-policy enforcement invariants — co-extrusion for s5_41 (Option B).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves policy-as-code
enforcement -- allowed instruments, per-issuer exposure caps, and max single-issuer concentration -- checked against
existing governed positions and refused fail-closed. Policy optimization is analytics (S5-V17), not tested here."""
from decimal import Decimal

from sovereign_agent.financials import check_investment

POLICY = {
    "allowed_instruments": ["bond", "note", "tbill"],
    "issuer_caps": {"ACME": "1000000"},
    "max_concentration": "0.40",
}


def test_allowed_move_passes():
    # a diversified existing base (each ~33%); a small add to UST keeps its share under the 40% concentration cap
    existing = [
        {"issuer": "UST", "instrument": "tbill", "currency": "USD", "amount": "300000"},
        {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "300000"},
        {"issuer": "MUNI", "instrument": "bond", "currency": "USD", "amount": "300000"},
    ]
    r = check_investment(POLICY, {"issuer": "UST", "instrument": "tbill", "currency": "USD", "amount": "50000"}, existing)
    assert r["ok"] is True and r["violations"] == []   # UST post 350k / 950k = 0.368 < 0.40; tbill allowed; no UST cap


def test_disallowed_instrument_is_refused():
    r = check_investment(POLICY, {"issuer": "UST", "instrument": "crypto", "currency": "USD", "amount": "1"}, [])
    assert r["ok"] is False
    assert any("not in policy allowed set" in v for v in r["violations"])


def test_issuer_cap_breach_is_refused():
    existing = [{"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "800000"}]
    r = check_investment(POLICY, {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "300000"}, existing)
    assert r["ok"] is False
    assert any("exceeds cap" in v for v in r["violations"])  # 1,100,000 > 1,000,000


def test_concentration_breach_is_refused():
    # existing: UST 100k; proposed ACME 200k -> ACME share = 200k/300k = 0.667 > 0.40
    existing = [{"issuer": "UST", "instrument": "tbill", "currency": "USD", "amount": "100000"}]
    r = check_investment(POLICY, {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "200000"}, existing)
    assert r["ok"] is False
    assert any("concentration" in v for v in r["violations"])


def test_within_concentration_passes():
    # existing: UST 700k; proposed ACME 200k -> ACME share = 200k/900k = 0.222 < 0.40
    existing = [{"issuer": "UST", "instrument": "tbill", "currency": "USD", "amount": "700000"}]
    r = check_investment(POLICY, {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "200000"}, existing)
    assert r["ok"] is True
