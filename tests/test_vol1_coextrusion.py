"""Vol 1 co-extrusion tests — the trust layer *Sovereign Inference & Memory* describes, proven in code.

Each test asserts a specific book claim, so the Tech/Arch board (17.6) can check book↔code↔test coherence:
  Ch 2 SIX routing + structural RED-barring · Ch 3 the 9-field receipt + chain · Ch 4 B51 curation +
  Merkle integrity + voice-routes-never-rules.
"""
import pytest

from sovereign_agent.inference import receipts as R
from sovereign_agent.inference.six import (
    SIXExchange, SensitivityClass, RedRoutingBarred, classify, route,
)
from sovereign_agent.memory.b51 import B51Stream, VoiceRuledError, merkle_root


# ── Ch 3 — receipts as constitutional anchors ──────────────────────────────────────────────────────
def test_receipt_has_nine_fields_and_validates():
    r = R.build_receipt(model_identity="sov-frontier-v2", input_content="Q3 actuals",
                        output_content="Q3 forecast", sensitivity_class="YELLOW",
                        routing_decision={"lane": "proposal_inference_lane", "platform": "local_sovereign"},
                        operator_identity="KM-1176",
                        constitutional_reference={"role_spec": "cfo_agent", "charter_clause": "c#yellow"})
    assert all(f in r for f in R.REQUIRED_FIELDS)        # all nine present (Ch 3)
    ok, why = R.validate_receipt(r)
    assert ok, why
    assert r["input_hash"].startswith("sha256:") and r["operator_identity"] == "KM-1176"


def test_tampered_receipt_fails_validation():
    r = R.build_receipt(model_identity="m", input_content="a", output_content="b",
                        sensitivity_class="GREEN", routing_decision={"lane": "routine_inference_lane"},
                        operator_identity="KM-1176", constitutional_reference={"role_spec": "x"})
    r["sensitivity_class"] = "RED"        # modify a field after signing
    ok, why = R.validate_receipt(r)
    assert not ok and "modified after signing" in why[0]


def test_receipt_chain_verifies_and_breaks_on_fork():
    ex = SIXExchange(operator_identity="KM-1176")
    chain = [ex.run(model_identity="m", input_content=f"in{i}", output_content=f"out{i}",
                    has_sensitive_content=False, touches_constitutional_surface=False,
                    role_authorized_class="GREEN", role_spec="synthesis_agent") for i in range(4)]
    assert R.verify_chain(chain) is True
    chain[2]["chain_reference"]["prior_cylinder"] = "forged"
    assert R.verify_chain(chain) is False


# ── Ch 2 — SIX sensitivity routing + structural enforcement ────────────────────────────────────────
def test_classification_three_classes():
    assert classify(has_sensitive_content=False, touches_constitutional_surface=False,
                    role_authorized_class="GREEN") == SensitivityClass.GREEN
    assert classify(has_sensitive_content=True, touches_constitutional_surface=False,
                    role_authorized_class="YELLOW") == SensitivityClass.YELLOW
    assert classify(has_sensitive_content=True, touches_constitutional_surface=True,
                    role_authorized_class="RED") == SensitivityClass.RED


def test_red_material_is_structurally_barred_from_external():
    # The defining Ch 2 claim: RED never routes externally — the harness refuses, loudly.
    with pytest.raises(RedRoutingBarred):
        route(SensitivityClass.RED, external=True)
    # local RED is fine
    assert route(SensitivityClass.RED, external=False)["platform"] == "local_sovereign"


def test_six_run_bars_red_external_and_receipts_the_decision():
    ex = SIXExchange(operator_identity="KM-1176")
    # a constitutional-surface input requested external → barred structurally
    with pytest.raises(RedRoutingBarred):
        ex.run(model_identity="m", input_content="amend the Charter", output_content="proposal",
               has_sensitive_content=True, touches_constitutional_surface=True,
               role_authorized_class="RED", role_spec="compliance_agent", external_requested=True)
    # a GREEN routine routes + produces a valid receipt
    rc = ex.run(model_identity="m", input_content="peer health", output_content="ok",
                has_sensitive_content=False, touches_constitutional_surface=False,
                role_authorized_class="GREEN", role_spec="synthesis_agent")
    assert rc["sensitivity_class"] == "GREEN"
    assert R.validate_receipt(rc)[0]


# ── Ch 4 — B51 attention stream ────────────────────────────────────────────────────────────────────
def _events(n):
    return [{"id": i, "kind": ("anomaly" if i % 50 == 0 else "routine"), "content": f"event {i}"} for i in range(n)]


def test_b51_compresses_and_proves_considered_set():
    b = B51Stream(curator_role="synthesis_agent")
    evs = _events(1000)
    out = b.curate(evs, surface=lambda e: e["kind"] == "anomaly")
    assert out["considered"] == 1000
    assert out["surfaced_count"] == 20          # ~1% surfaced → ~50× compression
    assert out["compression_ratio"] >= 40
    # Merkle root proves the curator saw the WHOLE set; dropping one event changes the root
    root_full = b.considered_root(evs)
    assert out["considered_merkle_root"] == root_full
    assert b.considered_root(evs[:-1]) != root_full


def test_b51_deny_suppresses_future_surfacing():
    b = B51Stream(curator_role="synthesis_agent")
    evs = [{"id": 1, "kind": "anomaly", "content": "x"}, {"id": 2, "kind": "anomaly", "content": "y"}]
    first = b.curate(evs, surface=lambda e: True)
    assert first["surfaced_count"] == 2
    b.deny(evs[0])
    second = b.curate(evs, surface=lambda e: True)
    assert second["surfaced_count"] == 1        # denied entry no longer surfaced (reversibility)


def test_voice_routes_attention_but_never_rules():
    b = B51Stream(curator_role="synthesis_agent")
    routed = B51Stream.voice_route({"id": 7})
    assert routed["action"] == "attention_routed" and routed["constitutional_effect"] is None
    with pytest.raises(VoiceRuledError):
        B51Stream.rules("approve all of these")   # voice can never rule on authorization


def test_merkle_root_deterministic():
    assert merkle_root(["a", "b", "c"]) == merkle_root(["a", "b", "c"])
    assert merkle_root(["a", "b"]) != merkle_root(["a", "c"])


# ── TA-1: sealed substrate + real P1 signing (the gap the Tech/Arch board found, now closed) ──────────
def test_receipt_is_p1_signed_when_sealed_present():
    from sovereign_agent.inference import primitives as P
    ident = P.new_identity()
    if not ident:
        pytest.skip("sealed primitives absent — stdlib fallback (demo mode)")
    r = R.build_receipt(model_identity="m", input_content="a", output_content="b",
                        sensitivity_class="YELLOW", routing_decision={"lane": "proposal_inference_lane"},
                        operator_identity="KM-1176", constitutional_reference={"role_spec": "cfo_agent"},
                        operator_private_key=ident["private_key"], operator_public_key=ident["public_key"])
    assert r.get("p1_signature") and r["p1_signature"]["alg"] == "P1-ECDSA-secp256k1"
    ok, why = R.validate_receipt(r)
    assert ok, why                                  # P1 signature verifies
    r["p1_signature"]["s"] += 1                     # tamper the signature
    ok2, why2 = R.validate_receipt(r)
    assert not ok2 and "P1 signature does not verify" in why2[0]
