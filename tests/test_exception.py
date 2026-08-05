"""Exception & governance workflows (s5_29 / reading Vol 31) — proof that the exception primitive ROUTES to the sealed
human gate and RESOLVES fail-closed, composing the sealed gates and adding no second approval engine.

Pure composition (no ledger, no merkle) — runs green on a bare public clone; no substrate guard needed."""
import pytest

from sovereign_agent.governance import exception as ex
from sovereign_agent.governance.exception import ExceptionError

# The sealed gate's own inputs (Compliance & Audit): a class the policy deems high-materiality forces a human;
# an unlisted class does not. role_spec carries no Charter-V.7-forbidden classes here.
POLICY = {"high_materiality_classes": ["credit_limit_override"]}
ROLE_SPEC = {"charter_v7_forbidden_classes": []}


def _open(exc_id="EXC-1", action_class="credit_limit_override", mandate="M-CREDIT", materiality="high"):
    return ex.open_exception(exc_id, action_class, mandate, "a limit was breached", materiality)


# --- routing: the sealed human gate decides; this module does not re-decide -------------------------------------

def test_material_exception_requiring_a_human_routes_to_a_pending_gate_case():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    assert routed["status"] == "pending_gate"
    # a genuine GRC case was opened and its detect step stamped — composed, not re-implemented
    assert routed["case"]["case"] == "EXC-1"
    assert routed["case"]["done"] == ["detect"]
    assert routed["case"]["state"] == "in_progress"


def test_material_exception_no_gate_would_catch_is_refused_default_deny():
    # action_class the policy does NOT gate + material → refused, never silently auto-resolved
    exc = _open(action_class="unlisted_deviation", materiality="high")
    with pytest.raises(ExceptionError, match="must pass a gate"):
        ex.route(exc, POLICY, ROLE_SPEC)


def test_immaterial_exception_the_gate_ignores_auto_resolves():
    exc = _open(action_class="unlisted_deviation", materiality="low")
    routed = ex.route(exc, POLICY, ROLE_SPEC)
    assert routed["status"] == "auto_resolved"
    assert "case" not in routed


def test_non_regulated_mode_never_forces_a_human_so_material_is_refused():
    # requires_approval returns False outside corporate_regulated mode → a material exception is refused, not waved
    with pytest.raises(ExceptionError, match="must pass a gate"):
        ex.route(_open(), POLICY, ROLE_SPEC, mode="standard")


def test_route_twice_is_refused():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    with pytest.raises(ExceptionError, match="not 'open'"):
        ex.route(routed, POLICY, ROLE_SPEC)


# --- resolution: fail-closed on the sealed mandate guard AND the sealed GRC sign-off -----------------------------

def test_resolution_by_mandate_holder_with_clean_checks_resolves_and_closes_the_case():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    approval = {"held_mandates": ["M-CREDIT"], "approver": "controller-jane"}
    resolved = ex.resolve(routed, approval, checks_results=[])
    assert resolved["status"] == "resolved"
    assert resolved["resolved_by"] == "controller-jane"
    # the sealed GRC case was signed off through its full ordered lifecycle
    assert resolved["case"]["state"] == "closed"
    assert resolved["case"]["signed_off"] is True
    assert resolved["case"]["done"] == ["detect", "review", "resolve"]


def test_resolution_by_a_party_without_the_mandate_is_barred():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    # holds a different mandate → the sealed mandate guard bars it, disposition notwithstanding
    approval = {"held_mandates": ["M-TREASURY"], "approver": "someone-else"}
    with pytest.raises(ExceptionError, match="does not hold the exception's mandate"):
        ex.resolve(routed, approval)


def test_resolution_via_declared_cross_mandate_authorization_is_allowed():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    approval = {
        "cross_mandate_auth": {"authorized": True, "mandate": "M-CREDIT"},
        "approver": "cross-signer",
    }
    resolved = ex.resolve(routed, approval, checks_results=[])
    assert resolved["status"] == "resolved"


def test_resolution_without_a_named_approver_is_refused():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    with pytest.raises(ExceptionError, match="named human approver"):
        ex.resolve(routed, {"held_mandates": ["M-CREDIT"]})


def test_resolution_against_an_open_compliance_gap_is_refused_by_the_grc_signoff():
    routed = ex.route(_open(), POLICY, ROLE_SPEC)
    approval = {"held_mandates": ["M-CREDIT"], "approver": "controller-jane"}
    open_gap = [{"check": "segregation_of_duties", "passed": False, "gap": "same-person breach"}]
    with pytest.raises(Exception, match="open compliance gap"):
        ex.resolve(routed, approval, checks_results=open_gap)


def test_an_auto_resolved_or_unrouted_exception_has_no_gate_to_resolve_through():
    auto = ex.route(_open(action_class="unlisted_deviation", materiality="low"), POLICY, ROLE_SPEC)
    with pytest.raises(ExceptionError, match="not 'pending_gate'"):
        ex.resolve(auto, {"held_mandates": ["M-CREDIT"], "approver": "x"})


# --- scale: the same primitive per exception, nothing silently waved through ------------------------------------

def test_route_batch_splits_a_high_volume_queue_by_disposition_and_names_refusals():
    batch = [
        _open("EXC-A", action_class="credit_limit_override", materiality="high"),   # → pending_gate
        _open("EXC-B", action_class="unlisted_deviation", materiality="low"),        # → auto_resolved
        _open("EXC-C", action_class="unlisted_deviation", materiality="high"),       # → refused (policy gap)
    ]
    out = ex.route_batch(batch, POLICY, ROLE_SPEC)
    assert out["total"] == 3
    assert [r["exception"] for r in out["pending_gate"]] == ["EXC-A"]
    assert [r["exception"] for r in out["auto_resolved"]] == ["EXC-B"]
    assert [r["exception"] for r in out["refused"]] == ["EXC-C"]
    assert "must pass a gate" in out["refused"][0]["reason"]
