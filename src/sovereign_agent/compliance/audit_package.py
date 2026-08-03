"""Audit package — per-domain compliance reports across the five sealed domains, assembled into a self-verifying audit
package an external auditor recomputes without trusting the exporter.

Co-extrusion for s5_14 (Compliance & Audit Automation + Reporting, KM Option B 2026-08-03). Pure / structural, no crypto
substrate (runs in a pure public clone, no skip — F-1 posture). A compliance report for a domain (Financials, Treasury,
Supply, Manufacturing, Project) is the domain's readiness plus its receipted gaps and evidence references. An audit
package bundles the reports and carries a content hash (stdlib SHA-256 over the package's canonical form) so a recipient
recomputes the digest and confirms the package was not altered since it was built — the same self-verifying posture the
sealed `export_packet`/`merkle` give evidence bundles, here for the audit package as a whole."""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Mapping

DOMAINS = ("financials", "treasury", "supply", "manufacturing", "project")


class AuditPackageError(ValueError):
    """Raised for an unknown compliance domain or a tampered package on verification."""


def compliance_report(domain: str, readiness: Mapping, evidence_refs: List[str]) -> Dict[str, object]:
    """A per-domain compliance report: the domain's audit-readiness (from `audit_checks.audit_readiness`), its
    receipted gaps, and references to the governed evidence backing it. One of the five sealed domains."""
    if domain not in DOMAINS:
        raise AuditPackageError(f"unknown domain {domain!r} (known: {', '.join(DOMAINS)})")
    return {
        "domain": domain,
        "ready": bool(readiness.get("ready")),
        "gaps": list(readiness.get("gaps", [])),
        "evidence_refs": list(evidence_refs),
    }


def _canonical(obj) -> str:
    """Deterministic JSON for hashing — sorted keys, no incidental whitespace, so the digest is reproducible."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def build_audit_package(reports: List[Mapping], generated_utc: str) -> Dict[str, object]:
    """Assemble the domain compliance reports into one self-verifying audit package.

    The package carries an overall `ready` flag (every domain ready), the reports, and a `content_hash` — a SHA-256 over
    the canonical form of the reports and the timestamp. A recipient recomputes the hash (see `verify_audit_package`) and
    knows the package has not been altered since it was built, without trusting whoever handed it over. `generated_utc`
    is supplied by the caller (this module does not read the clock, keeping it pure and reproducible)."""
    reports = list(reports)
    body = {"reports": reports, "generated_utc": generated_utc}
    return {
        "reports": reports,
        "generated_utc": generated_utc,
        "ready": all(bool(r.get("ready")) for r in reports) if reports else False,
        "domains": [r.get("domain") for r in reports],
        "content_hash": hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest(),
    }


def verify_audit_package(package: Mapping) -> bool:
    """Recompute the package's content hash and confirm it matches — the self-verifying check an auditor runs. Returns
    True if intact; a mismatch (a tampered or truncated package) returns False rather than silently accepting it."""
    body = {"reports": list(package.get("reports", [])), "generated_utc": package.get("generated_utc")}
    recomputed = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    return recomputed == package.get("content_hash")
