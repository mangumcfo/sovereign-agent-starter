"""Clean-exit invariants — co-extrusion for s5_37 (The Clean Exit, escape arc 4/4, the terminal / LGP culmination).

Pure/structural: composes the sealed floors — the migration primitive (merkle provenance) and the sealed self-verifying
audit package. Proves a carve-out separates a subset of a consolidated group value-conserving (the carved-out unit plus
the remaining business conserve the whole; an entity not in the group is refused), that a diligence package anchors the
carved-out ledger to a provenance root and self-verifies (and a tampered package does not), and that a clean exit is
fail-closed (clean only if the carve-out conserves AND the package verifies)."""
from decimal import Decimal
import pytest
from sovereign_agent.deal.clean_exit import (
    carve_out, diligence_package, assert_clean_exit, CleanExitError,
)

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD, KM 2026-08-05 — merkle provenance needs the substrate)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

# A consolidated group: three entities, each a small ledger (signed).
GROUP = {
    "EntA": {"1000-Cash": "4000", "3000-Equity": "-4000"},
    "EntB": {"1000-Cash": "1500", "2000-AP": "-500", "3000-Equity": "-1000"},
    "EntC": {"1000-Cash": "800", "3000-Equity": "-800"},
}
EVID = ["hash:aa11", "hash:bb22"]


def test_carve_out_conserves_and_partitions():
    co = carve_out(GROUP, ["EntB"])
    assert co["conserves"] is True
    assert set(co["carved"]) == {"EntB"} and set(co["remaining"]) == {"EntA", "EntC"}
    assert co["carved_total"] + co["remaining_total"] == co["group_total"]


def test_carve_out_refuses_unknown_entity():
    with pytest.raises(CleanExitError):
        carve_out(GROUP, ["EntZ"])                                            # not in the group


def test_diligence_package_verifies_and_anchors():
    co = carve_out(GROUP, ["EntB"])
    dp = diligence_package("DEAL-1", co["carved"], EVID, "20260805T000000Z")
    assert dp["verified"] is True and dp["ledger_root"]
    assert dp["audit_package"]["domains"] == ["financials"]


def test_tampered_diligence_package_does_not_verify():
    from sovereign_agent.compliance.audit_package import verify_audit_package
    co = carve_out(GROUP, ["EntB"])
    dp = diligence_package("DEAL-2", co["carved"], EVID, "20260805T000000Z")
    pkg = dp["audit_package"]
    pkg["reports"][0]["evidence_refs"].append("hash:forged")                  # tamper after the hash was fixed
    assert verify_audit_package(pkg) is False                                 # content hash no longer matches


def test_assert_clean_exit_clean():
    art = assert_clean_exit("DEAL-3", GROUP, ["EntB"], EVID, "20260805T000000Z")
    assert art["clean"] is True and art["carve_out"]["conserves"] and art["diligence"]["verified"]


def test_assert_clean_exit_refuses_unknown_entity():
    with pytest.raises(CleanExitError):
        assert_clean_exit("DEAL-4", GROUP, ["EntZ"], EVID, "20260805T000000Z")


def test_ledger_root_order_independent():
    r1 = diligence_package("D-a", carve_out(GROUP, ["EntA", "EntB"])["carved"], EVID, "20260805T000000Z")["ledger_root"]
    r2 = diligence_package("D-b", carve_out(GROUP, ["EntB", "EntA"])["carved"], EVID, "20260805T000000Z")["ledger_root"]
    assert r1 == r2 and r1                                                    # provenance depends on the SET, not order


def test_gaps_disclosed_but_package_still_verifies():
    co = carve_out(GROUP, ["EntB"])
    dr = {"financials": {"ready": False, "gaps": ["open intercompany balance"]}}
    dp = diligence_package("DEAL-5", co["carved"], EVID, "20260805T000000Z", domain_readiness=dr)
    assert dp["verified"] is True                                            # an honest package verifies even with gaps
    assert dp["audit_package"]["ready"] is False                             # ... and discloses it is not fully ready
    assert dp["audit_package"]["reports"][0]["gaps"] == ["open intercompany balance"]
