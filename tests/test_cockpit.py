# -*- coding: utf-8 -*-
"""Acceptance tests for Atrium as Living OS (S8 Vol 4) — compose_cockpit.

Proves the host composes, never owns: it renders through the governed token set (V03 → V01), writes
ONLY through the V02 breath-gate (no direct write path), and its LGP Watch renders the economic-value
state READ-ONLY — displaying the objective, never running or optimizing the engines. Composes
V01/V02/V03 + yield_organism (read-only). Crypto-free.
"""
import dataclasses
import pytest

from sovereign_agent.sovereign_ux.cockpit import compose_cockpit, Cockpit
from sovereign_agent.sovereign_ux.tokens import TokenSet, TokenDrift
from sovereign_agent.sovereign_ux.gate_interaction import GateDenied
from sovereign_agent.obligations.ledger import ObligationLedger

_TOKENS = TokenSet(name="ridgeline.brand", tokens={"brand.primary": "#0B2A4A", "space.md": 16})


def _approving_gate(action, obligation):
    return {"status": "approved"}


# ---- render: through the governed token set (V03 -> V01) --------------------------------------

def test_render_goes_through_the_governed_tokens():
    ck = compose_cockpit(token_set=_TOKENS)
    view = ck.render({"header": {"color": "$brand.primary", "pad": "$space.md"}})
    assert view.content == {"header": {"color": "#0B2A4A", "pad": 16}}


def test_render_refuses_an_off_token(inherits_v03=True):
    ck = compose_cockpit(token_set=_TOKENS)
    with pytest.raises(TokenDrift):
        ck.render({"color": "$brand.NEON"})  # inherits V03's off-token refusal


# ---- write: ONLY through the V02 breath-gate -------------------------------------------------

def test_cockpit_has_no_direct_write_method():
    # the cockpit exposes render/propose/pending/dispose/lgp_watch — and NO mutate/save/write/apply
    public = {m for m in dir(Cockpit) if not m.startswith("_")}
    forbidden = {"write", "save", "commit", "apply", "mutate", "set", "update", "run", "optimize", "execute"}
    assert not (public & forbidden), f"cockpit exposes a forbidden mutation method: {public & forbidden}"


def test_write_path_requires_the_ledger():
    ck = compose_cockpit(token_set=_TOKENS)  # no ledger
    with pytest.raises(ValueError):
        ck.propose("do a thing")  # the cockpit writes only through the gate, never directly


def test_propose_and_dispose_go_through_the_gate(tmp_path):
    L = ObligationLedger(root=tmp_path / "obl", gate=_approving_gate)
    ck = compose_cockpit(token_set=_TOKENS, ledger=L)
    oid = ck.propose("rename a label", material=True)
    assert any((e.get("id")) == oid for e in ck.pending())
    ck.dispose(oid, approver="operator", evidence="applied; artifact /ridgeline/x.txt present")
    assert not any((e.get("id")) == oid for e in ck.pending())


def test_material_dispose_without_a_gate_is_denied(tmp_path):
    L = ObligationLedger(root=tmp_path / "obl")  # gate-less
    ck = compose_cockpit(token_set=_TOKENS, ledger=L)
    oid = ck.propose("materially binding", material=True)
    with pytest.raises(GateDenied):
        ck.dispose(oid, approver="operator", evidence="artifact present")  # AH-1 deny-by-default


# ---- LGP Watch: render read-only, never run or optimize --------------------------------------

def test_lgp_watch_renders_yield_state_read_only():
    ck = compose_cockpit(token_set=_TOKENS)
    yield_state = {"amm_pool": {"reserve_a": 1000, "reserve_b": 2000}, "payout_schedule": "monthly",
                   "recirc_allocation": 0.15}
    view = ck.lgp_watch(yield_state)
    assert view.content["amm_pool"] == {"reserve_a": 1000, "reserve_b": 2000}
    assert view.content["recirc_allocation"] == 0.15


def test_lgp_watch_does_not_mutate_the_state():
    ck = compose_cockpit(token_set=_TOKENS)
    state = {"amm_pool": {"reserve_a": 1000}}
    view = ck.lgp_watch(state)
    view.content["amm_pool"]["reserve_a"] = 0  # mutating the rendered view
    assert state == {"amm_pool": {"reserve_a": 1000}}  # the source economic state is untouched


def test_cockpit_does_not_import_a_yield_engine():
    # LGP Watch DISPLAYS the objective; the cockpit never runs/optimizes an engine — it imports none.
    from sovereign_agent.sovereign_ux import cockpit as ck
    src = open(ck.__file__).read()
    assert "amm_pool" not in src.replace("amm-pool", "")  # no import of the AMM engine (prose 'amm-pool' ok)
    assert "payout_engine" not in src and "import" not in src.split("yield_organism")[0].split("\n")[-1]


# ---- composition boundary: composes V01/V02/V03 ----------------------------------------------

def test_composes_the_operator_layer_volumes():
    from sovereign_agent.sovereign_ux import cockpit as ck
    from sovereign_agent.sovereign_ux.tokens import apply_tokens as v3
    from sovereign_agent.sovereign_ux.gate_interaction import propose as v2, dispose as v2d
    from sovereign_agent.sovereign_ux.lens import View as v1
    assert ck.apply_tokens is v3          # V03 (which composes V01)
    assert ck.propose is v2 and ck.dispose is v2d  # V02
    assert ck.View is v1                  # V01


def test_cockpit_is_frozen():
    ck = compose_cockpit(token_set=_TOKENS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ck.token_set = None  # type: ignore[misc] — a composition, not a mutable host
