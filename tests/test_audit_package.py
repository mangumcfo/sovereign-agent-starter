"""Audit-package invariants — co-extrusion for s5_14 (Option B).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves per-domain compliance
reports across the five sealed domains and a self-verifying audit package -- a content hash a recipient recomputes,
detecting any tamper -- without invoking the sealed crypto substrate (stdlib SHA-256, pure)."""
import pytest

from sovereign_agent.compliance.audit_package import (
    compliance_report, build_audit_package, verify_audit_package, AuditPackageError, DOMAINS,
)


def _report(domain, ready, gaps=()):
    return compliance_report(domain, {"ready": ready, "gaps": list(gaps)}, evidence_refs=[f"{domain}:ev1"])


def test_compliance_report_for_each_sealed_domain():
    assert set(DOMAINS) == {"financials", "treasury", "supply", "manufacturing", "project"}
    r = _report("manufacturing", True)
    assert r["domain"] == "manufacturing" and r["ready"] is True and r["evidence_refs"] == ["manufacturing:ev1"]


def test_unknown_domain_refused():
    with pytest.raises(AuditPackageError):
        compliance_report("marketing", {"ready": True}, [])


def test_package_ready_only_when_all_domains_ready():
    reports = [_report(d, True) for d in DOMAINS]
    pkg = build_audit_package(reports, generated_utc="2026-07-31T00:00:00Z")
    assert pkg["ready"] is True and set(pkg["domains"]) == set(DOMAINS)
    # one domain with a gap -> package not ready
    reports2 = [_report("financials", False, gaps=[{"check": "X", "gap": "unbalanced"}])] + [_report(d, True) for d in DOMAINS[1:]]
    pkg2 = build_audit_package(reports2, generated_utc="2026-07-31T00:00:00Z")
    assert pkg2["ready"] is False


def test_package_is_self_verifying_and_detects_tamper():
    pkg = build_audit_package([_report(d, True) for d in DOMAINS], generated_utc="2026-07-31T00:00:00Z")
    assert verify_audit_package(pkg) is True
    # tamper: flip a domain's readiness without recomputing the hash -> verification fails
    pkg["reports"][0]["ready"] = False
    assert verify_audit_package(pkg) is False
