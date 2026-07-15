"""S4 Yield Engine 1.5 — economic/ verifiable-yield export (spec
artifacts/specs/verifiable_yield_export_v0.1.yaml).

Proves the sealed book's designed extension on the verified, crypto-free substrate — the economic/
bundle in src/sovereign_agent/yield_organism/economic_export.py (S2-V5 Ch8 "the auditor who re-ran the
yield from the bundle"):

  (a) the bundle assembles DETERMINISTICALLY — byte-identical on re-export (canonical sorted JSON);
  (b) verify_bundle PASSES on an honest bundle and SEPARATES reproducibility (VERIFIED, computed here)
      from signatures (SEALED_HOST_PENDING, the sealed-host seam — never faked);
  (c) TAMPER: altered value-flow amount FAILS naming the file; altered roll-up FAILS; manifest hash
      mismatch FAILS;
  (d) a value-flow referencing a nonexistent cylinder FAILS;
  (e) read-only invariant — export never mutates the obligation ledger;
  (f) e2e: projector -> scorer -> compounder -> export -> verify (all five slices compose).

These tests import economic_export.py directly (the linkage the extrusion harness expects).
"""
from decimal import Decimal

import pytest

from sovereign_agent.obligations.ledger import ObligationLedger
from sovereign_agent.yield_organism._sealed_host_seam import SEALED_HOST_PENDING
from sovereign_agent.yield_organism.alignment_scorer import AlignmentScorer
from sovereign_agent.yield_organism.compounding import BoundedCompounder, PeriodInput
from sovereign_agent.yield_organism.economic_export import (
    F_FLOWS,
    F_MANIFEST,
    F_ROLLUP,
    REPRO_FAILED,
    REPRO_VERIFIED,
    BundleVerification,
    EconomicBundleExporter,
    EconomicExportRefused,
    _sha,
)
from sovereign_agent.yield_organism.value_flow import ValueFlowProjector, WeightBasis


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────────
def _real_gate(action, obligation):
    return {"status": "approved", "real": True}


def _gated_ledger(tmp_path, name="obl"):
    return ObligationLedger(root=str(tmp_path / name), principal_id="owner", gate=_real_gate)


def _fully_aligned_cylinder(L, title, owner="holder-01", value="500"):
    ob = L.open(title, owner=owner, material=True,
                lgp={"economic_value": value, "denomination": "SLATE"})
    L.approve(ob["id"], approved_by="owner")
    L.close(ob["id"], evidence="/proof/artifact.txt sha256 " + "a" * 40, closed_by="owner")
    return ob


def _built_bundle(tmp_path):
    """Assemble an honest bundle end-to-end (projector -> scorer -> compounder -> export)."""
    L = _gated_ledger(tmp_path)
    rewards = [_fully_aligned_cylinder(L, f"reward r{i}", value="500") for i in range(3)]
    posture = AlignmentScorer(L).score(owner="holder-01")               # SUFFICIENT, weight 1.0
    flows = [ValueFlowProjector(L).project(ob["id"], WeightBasis.from_posture(posture))
             for ob in rewards]
    periods = [PeriodInput.of(flows, posture), PeriodInput.of([], posture)]
    record = BoundedCompounder().compound(periods)
    bundle = EconomicBundleExporter(L).export(
        flows=flows, posture=posture, periods=periods, compounding_record=record,
        rolling_window=12)
    return L, bundle


# ── (a) deterministic — byte-identical on re-export ───────────────────────────────────────────────
def _records(tmp_path):
    """Build a ledger + the yield records once (ledger ids are random — so determinism is asserted on
    RE-EXPORT of the SAME records, the real byte-identical contract)."""
    L = _gated_ledger(tmp_path)
    rewards = [_fully_aligned_cylinder(L, f"reward r{i}", value="500") for i in range(3)]
    posture = AlignmentScorer(L).score(owner="holder-01")
    flows = [ValueFlowProjector(L).project(ob["id"], WeightBasis.from_posture(posture))
             for ob in rewards]
    periods = [PeriodInput.of(flows, posture), PeriodInput.of([], posture)]
    record = BoundedCompounder().compound(periods)
    return L, dict(flows=flows, posture=posture, periods=periods, compounding_record=record,
                   rolling_window=12)


def test_bundle_assembles_deterministically(tmp_path):
    # re-export the SAME records twice -> byte-identical bundle (canonical sorted JSON, no timestamp/random).
    L, recs = _records(tmp_path)
    b1 = EconomicBundleExporter(L).export(**recs)
    b2 = EconomicBundleExporter(L).export(**recs)
    assert b1.files == b2.files
    assert b1.bundle_sha == b2.bundle_sha
    # the manifest is canonical and the bundle_sha is its sha256 (no float drift, sorted keys)
    assert b1.bundle_sha == _sha(b1.files[F_MANIFEST].encode("utf-8"))


def test_bundle_layout_has_all_economic_files(tmp_path):
    _, b = _built_bundle(tmp_path)
    assert set(b.files) == {"value_flows.ndjson", "posture.json", "compounding_rollup.json",
                            "reserve_state.json", "manifest.json"}
    assert b.manifest["money_path"] == "OFF"
    assert b.manifest["value_flow_count"] == 3
    assert b.manifest["signature"]["status"] == SEALED_HOST_PENDING     # crypto is the sealed-host seam
    assert b.manifest["inheritance_extension_point"]["status"] == "DECLARED"   # V4 extension point


def test_write_materializes_economic_subdir(tmp_path):
    _, b = _built_bundle(tmp_path)
    econ = b.write(tmp_path / "export")
    assert econ.name == "economic"
    assert (econ / "value_flows.ndjson").read_text() == b.files[F_FLOWS]
    assert (econ / "manifest.json").read_text() == b.files[F_MANIFEST]


# ── (b) verify PASSES + SEPARATES reproducibility (computed) from signatures (pending) ─────────────
def test_verify_passes_and_separates_reproducibility_from_signatures(tmp_path):
    _, b = _built_bundle(tmp_path)
    v = EconomicBundleExporter.verify_bundle(b)
    assert isinstance(v, BundleVerification)
    assert v.reproducible is True and bool(v) is True
    assert v.reproducibility == REPRO_VERIFIED                          # computed HERE
    assert v.signatures == SEALED_HOST_PENDING                          # sealed host — NOT faked True
    assert v.signatures != REPRO_VERIFIED                               # signatures never claim verified here
    assert all(v.checks.values())
    assert v.failures == ()
    assert "reproducibility: VERIFIED" in v.summary and "SEALED_HOST_PENDING" in v.summary


# ── (c) TAMPER — altered value-flow amount / roll-up / manifest hash all FAIL ─────────────────────
def test_tamper_altered_value_flow_amount_fails_naming_file(tmp_path):
    _, b = _built_bundle(tmp_path)
    # alter a byte in the value-flow ndjson body WITHOUT re-signing the manifest hash
    b.files[F_FLOWS] = b.files[F_FLOWS].replace("500", "999", 1)
    v = EconomicBundleExporter.verify_bundle(b)
    assert v.reproducible is False and v.reproducibility == REPRO_FAILED
    assert v.checks["manifest_hashes"] is False
    assert any(F_FLOWS in f for f in v.failures)                        # FAILS naming the file


def test_tamper_altered_rollup_fails_on_rederivation(tmp_path):
    """An attacker who CAN recompute a file hash (no signature) still cannot make the roll-up reproduce:
    reproducibility is not forgeable even when file-hash consistency is."""
    _, b = _built_bundle(tmp_path)
    import json
    rollup = json.loads(b.files[F_ROLLUP])
    # dishonestly inflate the recorded cumulative — then make the file hash self-consistent
    rollup["record"]["cumulative"] = str(Decimal(rollup["record"]["cumulative"]) + Decimal("1000000"))
    from sovereign_agent.yield_organism.economic_export import _canon_str
    b.files[F_ROLLUP] = _canon_str(rollup)
    manifest = json.loads(b.files[F_MANIFEST])
    manifest["files"][F_ROLLUP] = _sha(b.files[F_ROLLUP].encode("utf-8"))   # re-sign the file hash
    b.files[F_MANIFEST] = _canon_str(manifest)
    v = EconomicBundleExporter.verify_bundle(b)
    assert v.checks["manifest_hashes"] is True                          # file hashes now consistent
    assert v.checks["rollup_rederive"] is False                         # but the roll-up does NOT reproduce
    assert v.reproducible is False
    assert any(F_ROLLUP in f and "reproduce" in f for f in v.failures)


def test_tamper_manifest_hash_mismatch_fails(tmp_path):
    _, b = _built_bundle(tmp_path)
    import json
    manifest = json.loads(b.files[F_MANIFEST])
    manifest["files"][F_ROLLUP] = "deadbeef" * 8                        # a lie about the file hash
    from sovereign_agent.yield_organism.economic_export import _canon_str
    b.files[F_MANIFEST] = _canon_str(manifest)
    v = EconomicBundleExporter.verify_bundle(b)
    assert v.reproducible is False and v.checks["manifest_hashes"] is False
    assert any(F_ROLLUP in f for f in v.failures)


# ── (d) a value-flow referencing a nonexistent cylinder FAILS ─────────────────────────────────────
def test_value_flow_referencing_nonexistent_cylinder_fails(tmp_path):
    _, b = _built_bundle(tmp_path)
    import json
    lines = [ln for ln in b.files[F_FLOWS].splitlines() if ln.strip()]
    rec = json.loads(lines[0])
    rec["source_cylinder_id"] = "CYL-does-not-exist"                    # cite a phantom cylinder
    from sovereign_agent.yield_organism.economic_export import _canon_str
    lines[0] = _canon_str(rec)
    b.files[F_FLOWS] = "".join(ln + "\n" for ln in lines)
    manifest = json.loads(b.files[F_MANIFEST])
    manifest["files"][F_FLOWS] = _sha(b.files[F_FLOWS].encode("utf-8"))  # make the file hash consistent
    b.files[F_MANIFEST] = _canon_str(manifest)
    v = EconomicBundleExporter.verify_bundle(b)
    assert v.reproducible is False and v.checks["cylinders"] is False
    assert any("CYL-does-not-exist" in f for f in v.failures)


# ── (e) export REFUSES a non-completed compound (a brake state is not a disclosure) ───────────────
def test_export_refuses_paused_compound(tmp_path):
    from sovereign_agent.yield_organism.compounding import DriftBrake
    L = _gated_ledger(tmp_path)
    reward = _fully_aligned_cylinder(L, "r1")
    posture = AlignmentScorer(L).score(owner="holder-01")
    flow = ValueFlowProjector(L).project(reward["id"], WeightBasis.from_posture(posture))
    drifting = lambda: [{"id": "G-X9", "scope": "RED", "status": "OPEN"}]
    paused = BoundedCompounder().compound([PeriodInput.of([flow], posture)],
                                          brake=DriftBrake(signal_source=drifting, tolerance=0))
    assert paused.completed is False
    with pytest.raises(EconomicExportRefused, match="completed"):
        EconomicBundleExporter(L).export(flows=[flow], posture=posture,
                                         periods=[PeriodInput.of([flow], posture)],
                                         compounding_record=paused)


# ── (f) read-only invariant — export never mutates the ledger ─────────────────────────────────────
def test_export_is_read_only_over_ledger(tmp_path):
    L = _gated_ledger(tmp_path)
    _fully_aligned_cylinder(L, "r1")
    before = [dict(e) for e in L.iter_entries()]
    _built_bundle(tmp_path / "ro")   # a full export against its own ledger
    # and an export directly over L reads only:
    posture = AlignmentScorer(L).score(owner="holder-01")
    flows = [ValueFlowProjector(L).project(e["id"], WeightBasis.from_posture(posture))
             for e in L.iter_entries() if e.get("type") == "debit"]
    periods = [PeriodInput.of(flows, posture)]
    rec = BoundedCompounder().compound(periods)
    EconomicBundleExporter(L).export(flows=flows, posture=posture, periods=periods,
                                     compounding_record=rec)
    after = [dict(e) for e in L.iter_entries()]
    assert before == after                                             # byte-identical chain


# ── (f-e2e) the five slices compose: projector -> scorer -> compounder -> export -> verify ─────────
def test_e2e_all_five_slices_compose(tmp_path):
    L, b = _built_bundle(tmp_path)
    # the exported roll-up carries the real compounded numbers the compounder produced
    import json
    rollup = json.loads(b.files[F_ROLLUP])
    assert rollup["record"]["completed"] is True
    assert rollup["record"]["roll_ups"][0]["inflow"] == "1500"          # 3 x 500 projector flows summed
    # and the whole thing re-derives + separates the two verdicts
    v = EconomicBundleExporter.verify_bundle(b)
    assert v.reproducible is True
    assert v.reproducibility == REPRO_VERIFIED and v.signatures == SEALED_HOST_PENDING
