# -*- coding: utf-8 -*-
"""Acceptance tests for Zero-Trust UX (S8 Vol 7) — verify_surface.

Proves the surface shows what VERIFIED, not what is VOUCHED: a cleared proof from a named sealed floor
reads verified; a failed proof reads failed (never hidden); an absent, malformed, or merely-vouched
claim reads unverified (fail-closed, never passing). It runs no check of its own (no second verification
authority — imports only the Lens), renders read-only, and renders the in-tree evidence module read-only,
never as a floor. Crypto-free.
"""
import pytest

from sovereign_agent.sovereign_ux.verify_surface import (
    verify_surface, is_verified, evidence_view, VerifyStatus)
from sovereign_agent.sovereign_ux.lens import View


_CLEARED = {"proof": "cleared", "verified_by": "S7 Vol 4 Verified Flows"}
_FAILED = {"proof": "failed", "verified_by": "S7 Vol 2 Shields"}
_VOUCHED = {"asserted": True}                    # a claim with NO proof — vouched, not verified
_PROOFS = {"flow-a": _CLEARED, "shield-b": _FAILED, "claim-c": _VOUCHED}


# ---- shows what verified, not what is vouched -------------------------------------------------

def test_cleared_proof_reads_verified():
    v = verify_surface(_PROOFS)
    assert v.content["flow-a"]["status"] == "verified"
    assert v.content["flow-a"]["verified_by"] == "S7 Vol 4 Verified Flows"


def test_failed_proof_reads_failed_never_hidden():
    v = verify_surface(_PROOFS)
    assert v.content["shield-b"]["status"] == "failed"       # surfaced, not hidden
    assert v.content["shield-b"]["verified_by"] is None      # a failed proof verifies nothing


def test_vouched_claim_reads_unverified():
    # a claim asserted with no proof is VOUCHED, never verified
    v = verify_surface(_PROOFS)
    assert v.content["claim-c"]["status"] == "unverified"


# ---- adversarial clarity / fail-closed -------------------------------------------------------

def test_absent_claim_is_unverified():
    assert is_verified(_PROOFS, "not-present") is False       # absent -> not verified


def test_malformed_outcome_is_unverified():
    for bad in (None, "cleared", 42, ["cleared"], {"proof": "cleared"}):   # last: cleared but no verified_by
        assert VerifyStatus.of("x", bad).status == "unverified"


def test_is_verified_is_fail_closed():
    assert is_verified(_PROOFS, "flow-a") is True             # only a cleared proof from a named floor
    assert is_verified(_PROOFS, "shield-b") is False          # failed
    assert is_verified(_PROOFS, "claim-c") is False           # vouched
    # a 'cleared' with no naming floor does not pass — fail-closed
    assert is_verified({"z": {"proof": "cleared"}}, "z") is False


def test_cleared_but_unnamed_floor_is_not_verified():
    v = verify_surface({"z": {"proof": "cleared"}})           # no verified_by -> cannot be trusted
    assert v.content["z"]["status"] == "unverified"


# ---- no second verification authority · read-only · crypto-free ------------------------------

def test_surface_runs_no_check_imports_only_lens_no_engine():
    from sovereign_agent.sovereign_ux import verify_surface as vs
    import_lines = [ln for ln in open(vs.__file__).read().splitlines()
                    if ln.strip().startswith(("from ", "import ")) and "__future__" not in ln]
    joined = " ".join(import_lines)
    tokens = joined.replace("from", " ").replace("import", " ")
    assert ".lens" in joined                                  # composes the Lens for display
    for banned in ("shields", "verified_flows", "verify_flow", "attest", "evidence", "zero_trust",
                   "crypto", "hashlib", "secp256k1"):
        assert banned not in tokens, f"verify_surface must not import a verifier/engine: {banned}"


def test_surface_is_read_only():
    proofs = {"flow-a": {"proof": "cleared", "verified_by": "S7 Vol 4 Verified Flows", "meta": {"k": 1}}}
    v = verify_surface(proofs)
    v.content["flow-a"]["status"] = "TAMPERED"                # mutate the rendered view
    assert verify_surface(proofs).content["flow-a"]["status"] == "verified"   # source re-renders clean


def test_mandate_scoped():
    scope = {"auditor": ["flow-a"]}                            # auditor admitted only flow-a
    v = verify_surface(_PROOFS, mandate="auditor", scope=scope)
    assert "flow-a" in v.content and "shield-b" not in v.content


# ---- evidence rendered read-only, never a floor ----------------------------------------------

def test_evidence_rendered_read_only_not_a_floor():
    ev = {"actions": [{"id": 1, "kind": "export"}], "packet": "epk-9"}
    view = evidence_view(ev)
    assert isinstance(view, View) and view.content["packet"] == "epk-9"
    view.content["actions"][0]["kind"] = "MUT"                # mutate the rendered view
    assert ev["actions"][0]["kind"] == "export"               # the source evidence is untouched


def test_evidence_view_asserts_no_verified_status():
    # evidence is DISPLAYED, not verified — its view carries no 'verified' verdict of its own
    ev = {"actions": [], "packet": "epk-1"}
    view = evidence_view(ev)
    assert "status" not in view.content and "verified_by" not in view.content


# ---- composition boundary --------------------------------------------------------------------

def test_composes_the_lens_by_identity():
    from sovereign_agent.sovereign_ux import verify_surface as vs
    from sovereign_agent.sovereign_ux.lens import render_view as rv
    assert vs.render_view is rv                               # composes V01, not a re-implementation
