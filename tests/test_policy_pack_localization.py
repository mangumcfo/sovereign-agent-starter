"""Policy-pack localization substrate — the load-bearing PRESENT claim of S5-V? Sovereign Tax &
Statutory Localization (co-extrusion for s5_01, KM go 2026-08-03).

Proves the *mechanism* by which a statutory / localization pack becomes executable policy over the
sovereign core: a pack is a versioned policy file that the loader ingests, attests with a Merkle root,
and hot-reloads when its content changes. This is the substrate the tax volume claims PRESENT.

It does NOT build any real country's tax pack — the fixtures here are generic test policies, not a
jurisdiction. Real per-country packs (rates, e-invoicing formats, filing cadences) stay designed-toward
their own home (S5-V14 + the localization-pack spec); exists-on-roadmap != wired, per Framing A."""
from pathlib import Path

import yaml

from sovereign_agent.compliance.policy_loader import PolicyLoader
import pytest

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD, KM 2026-08-03)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")



def _write_pack(root: Path, pack_id: str, version: str, extra: dict | None = None) -> Path:
    d = root / "platform" / "governance_policies"
    d.mkdir(parents=True, exist_ok=True)
    content = {
        "id": pack_id,
        "version": version,
        "approval_requirements": {"statutory_filing": "human_gate"},
        "risk_scoring": {"base": 0.4},
    }
    if extra:
        content.update(extra)
    p = d / f"{pack_id}.policy.yaml"
    p.write_text(yaml.safe_dump(content, sort_keys=True))
    return p


def test_localization_pack_loads_versioned_and_merkle_attested(tmp_path):
    # A pack is loaded from the policy source, carries its declared version, and is Merkle-attested.
    _write_pack(tmp_path, "demo_locale_pack", "1.0")
    loader = PolicyLoader(primary_source=tmp_path)
    pol = loader.load_policy("demo_locale_pack")

    assert pol.id == "demo_locale_pack"
    assert pol.version == "1.0"
    assert pol.module_root and len(pol.module_root) == 64        # sha256 Merkle root over pack content
    assert "governance_policies" in pol.source_path             # loaded from the source, not the placeholder
    assert loader.list_loaded_policies()["demo_locale_pack"] == "1.0"
    assert loader.get_active_policy().module_root == pol.module_root


def test_pack_hot_reload_changes_version_and_attestation(tmp_path):
    # Adding to a pack (a dated, receipted change) yields a new version AND a new attestation root —
    # the pack cannot change silently. This is compliance-as-proof-by-construction at the pack layer.
    _write_pack(tmp_path, "demo_locale_pack", "1.0")
    loader = PolicyLoader(primary_source=tmp_path)
    v1 = loader.load_policy("demo_locale_pack")
    root_v1 = v1.module_root

    _write_pack(tmp_path, "demo_locale_pack", "1.1", extra={"retention_rules": {"invoice": "7y"}})
    v2 = loader.load_policy("demo_locale_pack", force_reload=True)

    assert v2.version == "1.1"
    assert v2.module_root != root_v1                            # content changed -> attestation changed
    assert v2.retention_rules.get("invoice") == "7y"


def test_missing_pack_is_placeholder_not_silent_localization(tmp_path):
    # A country whose pack does not exist must NOT masquerade as loaded/localized — the loader returns a
    # marked placeholder (version 0.0, source 'placeholder'), so exists != wired is observable, not hidden.
    loader = PolicyLoader(primary_source=tmp_path)     # empty source: no packs on disk
    pol = loader.load_policy("france_vat_2027")

    assert pol.version == "0.0"
    assert pol.source_path == "placeholder"
