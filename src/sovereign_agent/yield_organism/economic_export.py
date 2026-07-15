"""EconomicBundleExporter — the S4 Yield Engine's economic/ verifiable-yield export (spec
artifacts/specs/verifiable_yield_export_v0.1.yaml, slice 1.5, the Phase-1 CLOSER).

The sealed books name the model exactly:

  · **S2-V5 Ch8** (the auditor who re-ran the yield from the bundle): the constitutional
    verifiable-package (cylinder chain + Merkle proofs + public anchor, verified with bl-verify)
    ships TODAY. The DESIGNED extension: "the same bundle carries an `economic/` subdirectory
    (value-flow signatures, the autonomy-ledger posture, the compounding roll-up, reserve state),
    and the extended `verify.sh` lets the auditor *re-run the entire yield computation from the
    bundle* — confirming every value-flow references a real cylinder, every roll-up is reproducible
    from its inputs."
  · **S4-V4 Ch4** (the verifiable inheritance package): the heir-checkable package BUILDS ON this
    export — the extension point where an heir re-runs the verify from the bundle itself. Declared
    here as an extension point, NOT built in this slice.

This module ASSEMBLES the `economic/` subdirectory from live yield-organism records (the value-flows
from slice 1.1, the alignment posture from slice 1.2, the bounded-compounding roll-up from slice 1.3)
and RE-DERIVES the yield computation from the bundled inputs on verify — so the yield disclosure is
cryptographic proof rather than narrative.

The honest seam (Ch8's own): the REPRODUCIBILITY runs here, in pure Python, with no crypto — every
value-flow's source cylinder, and every roll-up, is re-derived and compared against the bundle. The
SIGNATURES (bl-sign of the value-flow records, bl-verify of the whole bundle against the public
anchor) route through `_sealed_host_seam.py` (the node lane) and are ABSENT in this env — they return the
explicit SEALED_HOST_PENDING / UNVERIFIED sentinels, NEVER a fake True. So `verify_bundle` reports two
separated verdicts: reproducibility = VERIFIED (computed here) vs signatures = SEALED_HOST_PENDING
(the node wires the crypto on the sealed host; nothing else in the export changes when he does).

Invariants (constitutional, non-negotiable):
  · money_path OFF — the export attributes, serializes, and PROVES value; it moves NOTHING. Every file
    and the manifest carry money_path: OFF. There is no settle/pay/transfer/disburse method anywhere.
  · read-only over the ledger — the exporter READS the cylinder chain (iter_entries) to build the
    accompanying chain data; it never writes the ledger.
  · deterministic — same records -> byte-identical bundle (canonical sorted JSON, no timestamp/random;
    Decimals serialized as exact strings — evidence law, no float drift). Re-export is byte-identical.
  · sealed_source_only — every value-flow references a REAL cylinder present in the accompanying chain
    data; a flow citing a cylinder absent from the chain FAILS verification (never a silent pass).
  · DIRECTIONAL never summed — a directional flow in a compounding period is REFUSED on re-derivation
    (the compounder's own law), surfaced as a reproducibility failure, never silently summed.
  · crypto-free — no breathline_primitives import; the ONLY crypto site is the _sealed_host_seam adapter.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, Sequence

from . import _sealed_host_seam as _seam
from .compounding import ROLLING_WINDOW_DEFAULT, BoundedCompounder, CompoundingRefused

VERSION = "econ-export/v0.1"
SPEC = "verifiable_yield_export_v0.1.yaml"

# ── the economic/ bundle file layout (S2-V5 Ch8) ──────────────────────────────
DIRNAME = "economic"
F_FLOWS = "value_flows.ndjson"        # the value-flow signatures — one signed record per line
F_POSTURE = "posture.json"            # the autonomy-ledger alignment posture (the compounding weight)
F_ROLLUP = "compounding_rollup.json"  # the bounded-compounding roll-up + its re-derivable inputs
F_RESERVE = "reserve_state.json"      # the reserve posture (declared; draw-down is human-gated)
F_MANIFEST = "manifest.json"          # per-file hashes + chain data + the signature seam
_DATA_FILES = (F_FLOWS, F_POSTURE, F_ROLLUP, F_RESERVE)   # the files the manifest hashes

# ── verify verdicts — reproducibility (computed here) is SEPARATE from signatures (sealed host) ──
REPRO_VERIFIED = "VERIFIED"
REPRO_FAILED = "FAILED"


class EconomicExportRefused(ValueError):
    """Loud refusal to assemble an economic bundle — a bad export never becomes a silent artifact.

    Raised when the compounding record is not a completed run (a paused/braked compound is a brake
    state, never a yield disclosure), or when a value-flow carries no source cylinder to reference.
    """


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(obj) -> bytes:
    """Canonical JSON bytes — deterministic (sorted keys, tight separators) for byte-identical output."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _canon_str(obj) -> str:
    return _canon(obj).decode("utf-8")


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise EconomicExportRefused(f"not a decimal: {value!r}") from exc


# ── lightweight shims used ONLY to re-derive the compound from the bundle (duck-typed inputs) ──
@dataclass(frozen=True)
class _BundledFlow:
    """A value-flow reconstructed from the bundle — the compounder duck-types on these two fields."""
    weighted_value: Decimal
    directional: bool = False
    source_cylinder_id: Optional[str] = None


@dataclass(frozen=True)
class _BundledPosture:
    """A posture reconstructed from the bundle — the compounder duck-types on .weight ([0,1])."""
    weight: Decimal


@dataclass(frozen=True)
class EconomicBundle:
    """The assembled economic/ subdirectory — a name->content map, the manifest, and the bundle sha.

    `files` is the on-disk truth (every value in the map is the exact file content). The manifest file
    (files[F_MANIFEST]) is the integrity index: per-file hashes + the cylinder chain data + the
    signature seam. `bundle_sha` is the sha256 over the canonical manifest — the one hash a signature
    would sign (SEALED-HOST seam). money_path OFF by construction.
    """
    files: dict           # name -> str (exact content; F_FLOWS..F_RESERVE + F_MANIFEST)
    manifest: dict        # the parsed manifest (also serialized in files[F_MANIFEST])
    bundle_sha: str       # sha256 over the canonical manifest

    def write(self, dest) -> Path:
        """Materialize the economic/ subdirectory under `dest` (dest/economic/<files>). Read-only over
        any ledger; this only writes the assembled bundle files. Returns the economic/ dir path."""
        out = Path(dest) / DIRNAME
        out.mkdir(parents=True, exist_ok=True)
        for name, content in self.files.items():
            (out / name).write_text(content, encoding="utf-8")
        return out


@dataclass(frozen=True)
class BundleVerification:
    """The two SEPARATED verdicts S2-V5 Ch8 requires: reproducibility (computed here) vs signatures
    (sealed host). `reproducible` is the part this env CAN prove — manifest hashes match, every
    value-flow references a real cylinder, and the roll-up re-derives from the bundled inputs. `signatures`
    is the crypto seam's own status (SEALED_HOST_PENDING until the node wires bl-verify) — it NEVER
    contributes to `reproducible` (a fabricated pass here would be a constitutional lie)."""
    reproducible: bool
    reproducibility: str          # REPRO_VERIFIED | REPRO_FAILED
    signatures: str               # SEALED_HOST_PENDING (from the seam — never faked VERIFIED here)
    checks: dict                  # {"manifest_hashes": bool, "cylinders": bool, "rollup_rederive": bool}
    failures: tuple               # loud, file-naming failure strings (empty iff reproducible)

    def __bool__(self) -> bool:
        return self.reproducible

    @property
    def summary(self) -> str:
        return (f"reproducibility: {self.reproducibility} (computed here) · "
                f"signatures: {self.signatures} (sealed host)"
                + ("" if self.reproducible else f" · failures: {list(self.failures)}"))


class EconomicBundleExporter:
    """Assembles + verifies the economic/ subdirectory of the constitutional verifiable-package.

    READS the obligation ledger's cylinder chain (iter_entries) to build the accompanying chain data;
    it never writes the ledger. There is deliberately NO settle/pay/transfer/disburse method — the
    absence is the money_path-OFF invariant. Deterministic + Decimal-exact throughout.
    """

    def __init__(self, ledger):
        # Duck-typed on the read API only (iter_entries) — the exporter never touches a write method.
        self.ledger = ledger

    # ── SEALED-HOST-SEAM: crypto wiring routes through yield_organism/_sealed_host_seam.py (the node lane).
    # Signing each value-flow record (sign_value_flow) and bl-verify of the whole bundle against the
    # published anchor (verify_economic_bundle) are the crypto-engine ring — ABSENT in this env, stubbed
    # with explicit SEALED_HOST_PENDING / UNVERIFIED sentinels, never faked. The reproducibility proof
    # (below) needs no crypto and stands alone; the signature rides on top of it when the node wires it.

    def _cylinder_index(self) -> dict:
        """Read-only: {cylinder_id: chain_hash} for every sealed cylinder (debit) on the ledger chain.

        This is the accompanying chain data the economic bundle rides on — the constitutional package's
        cylinder chain, indexed so verify can confirm every value-flow references a REAL cylinder.
        """
        idx: dict = {}
        for e in self.ledger.iter_entries():
            if e.get("type") == "debit" and e.get("id"):
                idx[e["id"]] = e.get("hash")
        return idx

    @staticmethod
    def _flow_source(flow) -> str:
        cid = getattr(flow, "source_cylinder_id", None)
        if not cid:
            raise EconomicExportRefused(
                "value-flow carries no source_cylinder_id — a flow that references no cylinder cannot "
                "be exported (sealed_source_only: every flow replays a real cylinder)")
        return str(cid)

    def _serialize_periods(self, periods: Sequence) -> list:
        """Serialize the compounding period inputs so verify can re-derive the roll-up from them.

        Each period keeps its posture weight + its flows (source cylinder, weighted value, directional
        flag) — the minimal inputs the BoundedCompounder consumes. Order-preserving (compounding is
        order-sensitive)."""
        out = []
        for pin in periods:
            flows = []
            for f in getattr(pin, "flows", ()):
                flows.append({
                    "source_cylinder_id": self._flow_source(f),
                    "weighted_value": str(_dec(getattr(f, "weighted_value"))),
                    "directional": bool(getattr(f, "directional", False)),
                })
            out.append({
                "posture_weight": str(_dec(getattr(getattr(pin, "posture"), "weight"))),
                "flows": flows,
            })
        return out

    def export(self, *, flows, posture, periods, compounding_record,
               reserve_state: Optional[dict] = None,
               rolling_window: int = ROLLING_WINDOW_DEFAULT,
               generated_for: Optional[list] = None) -> EconomicBundle:
        """Assemble the economic/ bundle from live yield-organism records.

        flows            — the value-flow signatures set (ValueFlow, slice 1.1).
        posture          — the alignment posture (AlignmentPosture, slice 1.2).
        periods          — the compounding period inputs (PeriodInput, slice 1.3) — serialized so the
                           roll-up is re-derivable from them on verify.
        compounding_record — the bounded-compounding roll-up (CompoundingRecord, slice 1.3). MUST be a
                           completed run — a paused/braked compound is a brake state, not a disclosure.
        reserve_state    — optional reserve posture (declared; money_path is forced OFF).
        rolling_window   — the compounder window that produced the record (bundled so re-derivation uses it).
        """
        if not getattr(compounding_record, "completed", False):
            raise EconomicExportRefused(
                "compounding_record is not a completed run (paused/braked) — a brake state is not a yield "
                "disclosure; export only a completed compound (the brake is its own receipt)")

        cylinder_index = self._cylinder_index()

        # ── value_flows.ndjson — the signed value-flow records, deterministically ordered ──
        flow_dicts = []
        for f in flows:
            self._flow_source(f)                              # fail loud on a cylinder-less flow
            signed = _seam.sign_value_flow(f.to_dict())       # SEALED-HOST seam: pending signature, never faked
            flow_dicts.append(signed)
        flow_dicts.sort(key=lambda r: (str(r.get("source_cylinder_id")),
                                       str(r.get("receipt_id")), str(r.get("weighted_value"))))
        flows_content = "".join(_canon_str(r) + "\n" for r in flow_dicts)

        # ── posture.json ──
        posture_content = _canon_str(posture.to_dict())

        # ── compounding_rollup.json — the roll-up + the inputs it re-derives from ──
        rollup_obj = {
            "model": compounding_record.model,
            "rolling_window": int(rolling_window),
            "periods": self._serialize_periods(periods),
            "record": compounding_record.to_dict(),
        }
        rollup_content = _canon_str(rollup_obj)

        # ── reserve_state.json — declared reserve posture (draw-down is human-gated; money_path OFF) ──
        reserve_obj = dict(reserve_state) if reserve_state else {
            "reserve_type": "yield_risk_reserve",
            "status": "DECLARED",
            "committed_value": "0",
            "denomination": "units",
            "note": "S4-V3 Ch7 yield risk reserve — committed value against a bad year; draw-down only "
                    "through a human-gated proposal. Declared here (not drawn).",
        }
        reserve_obj["money_path"] = "OFF"                     # forced — a reserve never moves funds here
        reserve_content = _canon_str(reserve_obj)

        contents = {
            F_FLOWS: flows_content,
            F_POSTURE: posture_content,
            F_ROLLUP: rollup_content,
            F_RESERVE: reserve_content,
        }
        file_hashes = {name: _sha(contents[name].encode("utf-8")) for name in _DATA_FILES}

        gen_for = sorted(generated_for) if generated_for else sorted(
            {self._flow_source(f) for f in flows})

        manifest = {
            "version": VERSION,
            "spec": SPEC,
            "generated_for": gen_for,
            "money_path": "OFF",
            "value_flow_count": len(flow_dicts),
            "files": file_hashes,                             # per-file content hashes
            "cylinder_index": cylinder_index,                 # the accompanying chain data (read-only)
            "reproducibility_contract": (
                "every value-flow references a real cylinder in cylinder_index; the compounding record "
                "re-derives from periods (re-run BoundedCompounder(rolling_window) over the bundled "
                "inputs and compare); every file hash matches. Reproducibility is computed by verify; "
                "the cryptographic signature is the SEALED-HOST seam (the node lane)."),
            "signature": {                                    # SEALED-HOST seam — the node wires bl-sign
                "status": _seam.SEALED_HOST_PENDING,
                "signature": None,
                "note": "bl-sign of the bundle_sha + bl-verify against the published anchor route through "
                        "_sealed_host_seam.py; ABSENT in this env, never faked.",
            },
            "inheritance_extension_point": {                  # V4 — declared, NOT built here
                "target": "verifiable_inheritance_package (S4-V4 Ch4)",
                "status": "DECLARED",
                "note": "the heir-checkable package builds on this economic/ export — the extension point "
                        "where an heir re-runs verify from the bundle. Not built in this slice.",
            },
            "verify": "EconomicBundleExporter.verify_bundle(bundle)",
        }
        manifest_content = _canon_str(manifest)
        contents[F_MANIFEST] = manifest_content
        return EconomicBundle(files=contents, manifest=manifest,
                              bundle_sha=_sha(manifest_content.encode("utf-8")))

    # ── verification — reproducibility (computed here) SEPARATE from signatures (sealed host) ──
    @staticmethod
    def verify_bundle(bundle: EconomicBundle) -> BundleVerification:
        """RE-DERIVE the yield from the bundle. Reports reproducibility (what this env proves) SEPARATE
        from signatures (SEALED_HOST_PENDING). Never mutates anything; reads the bundle files only.

        Checks (all must pass for reproducibility):
          (a) manifest_hashes — every data-file's sha256 matches manifest.files (tamper of a file body
              FAILS, naming the file);
          (b) cylinders — every value-flow (in value_flows.ndjson AND in the roll-up's periods)
              references a cylinder present in manifest.cylinder_index (a flow citing a nonexistent
              cylinder FAILS);
          (c) rollup_rederive — re-run BoundedCompounder(rolling_window) over the bundled periods and
              compare to the bundled record (an altered roll-up FAILS; a DIRECTIONAL flow in a sum is
              REFUSED and surfaced).
        """
        files = bundle.files
        failures: list = []

        # signatures verdict — from the seam, NEVER faked. UNVERIFIED/PENDING both read as "not assured".
        sig_status = _seam.verify_economic_bundle(bundle.manifest)
        signatures = REPRO_VERIFIED if _seam.is_verified(sig_status) else _seam.SEALED_HOST_PENDING

        try:
            manifest = json.loads(files[F_MANIFEST])
        except (KeyError, ValueError):
            return BundleVerification(
                reproducible=False, reproducibility=REPRO_FAILED, signatures=signatures,
                checks={"manifest_hashes": False, "cylinders": False, "rollup_rederive": False},
                failures=("manifest.json missing or unparseable",))

        declared = manifest.get("files", {})
        cyl_index = manifest.get("cylinder_index", {})

        # (a) manifest_hashes
        hashes_ok = True
        for name in _DATA_FILES:
            if name not in files:
                failures.append(f"file '{name}' absent from bundle"); hashes_ok = False; continue
            actual = _sha(files[name].encode("utf-8"))
            if actual != declared.get(name):
                failures.append(f"file '{name}' hash mismatch — tampered or non-canonical"); hashes_ok = False

        # (b) cylinders — every value-flow references a real cylinder in the chain data.
        # Parsed through the ONE ndjson gateway (§1/G2) — text entry point for in-memory bundles.
        from ..ndjson import parse_ndjson_text  # noqa: PLC0415 — lazy, keeps module import-light
        cyl_ok = True
        flows_read = parse_ndjson_text(files.get(F_FLOWS, ""), source=F_FLOWS)
        if flows_read.repair_required:
            for q in flows_read.quarantined:
                failures.append(f"file '{F_FLOWS}' unparseable line quarantined: {q[:60]!r}")
            cyl_ok = False
        for rec in flows_read.entries:
            cid = rec.get("source_cylinder_id")
            if cid not in cyl_index:
                failures.append(
                    f"value-flow references cylinder '{cid}' absent from chain data (file '{F_FLOWS}')")
                cyl_ok = False

        # (c) rollup_rederive — re-run the compounder over the bundled inputs and compare
        rederive_ok = True
        try:
            rollup = json.loads(files.get(F_ROLLUP, ""))
        except ValueError:
            failures.append(f"file '{F_ROLLUP}' missing or unparseable")
            rollup, rederive_ok = None, False
        if rollup is not None:
            # every period-flow must ALSO reference a real cylinder
            for pd in rollup.get("periods", []):
                for f in pd.get("flows", []):
                    if f.get("source_cylinder_id") not in cyl_index:
                        failures.append(
                            f"roll-up period references cylinder '{f.get('source_cylinder_id')}' absent "
                            f"from chain data (file '{F_ROLLUP}')")
                        cyl_ok = False
            try:
                periods = []
                for pd in rollup.get("periods", []):
                    bflows = [_BundledFlow(weighted_value=Decimal(str(f["weighted_value"])),
                                           directional=bool(f.get("directional", False)),
                                           source_cylinder_id=f.get("source_cylinder_id"))
                              for f in pd.get("flows", [])]
                    periods.append(type("P", (), {"flows": tuple(bflows),
                                   "posture": _BundledPosture(weight=Decimal(str(pd["posture_weight"])))})())
                window = int(rollup.get("rolling_window", ROLLING_WINDOW_DEFAULT))
                recomputed = BoundedCompounder(rolling_window=window).compound(periods).to_dict()
                if recomputed != rollup.get("record"):
                    failures.append(
                        f"compounding roll-up does not reproduce from bundled inputs (file '{F_ROLLUP}')")
                    rederive_ok = False
            except CompoundingRefused as exc:
                failures.append(f"roll-up re-derivation refused (file '{F_ROLLUP}'): {exc}")
                rederive_ok = False
            except (KeyError, ValueError, TypeError) as exc:
                failures.append(f"roll-up inputs malformed (file '{F_ROLLUP}'): {exc}")
                rederive_ok = False

        reproducible = hashes_ok and cyl_ok and rederive_ok
        return BundleVerification(
            reproducible=reproducible,
            reproducibility=REPRO_VERIFIED if reproducible else REPRO_FAILED,
            signatures=signatures,
            checks={"manifest_hashes": hashes_ok, "cylinders": cyl_ok, "rollup_rederive": rederive_ok},
            failures=tuple(failures))
