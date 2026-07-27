"""S5-05-E3-1 · E3-3: manifests cut, verify by recompute, and chain."""
from sovereign_agent.objects.manifest import cut_manifest, verify_chain, verify_manifest
from sovereign_agent.objects.registry import ObjectRegistry


def _reg(tmp_path, n=5):
    reg = ObjectRegistry(str(tmp_path))
    for i in range(n):
        reg.append(f"vendor:V-{i}", {"terms": 30}, author="d.reyes",
                   source_ref=f"W9-{i}:file", at="2029-01-01", mandate="operating")
    return reg


def test_omitted_object_changes_manifest_root(tmp_path):
    reg = _reg(tmp_path)
    m = cut_manifest(reg, at="2029-12-31T23:59:59Z", period_end=True)
    full = reg.entries()
    ok, _ = verify_manifest(m, full)
    assert ok
    ok, recomputed = verify_manifest(m, full[:-1])  # one object omitted
    assert not ok and recomputed != m["root"]


def test_manifest_chain_links_prior_period_root(tmp_path):
    reg = _reg(tmp_path)
    m1 = cut_manifest(reg, at="2029-11-30", period_end=True)
    reg.append("vendor:V-99", {"terms": 45}, author="d.reyes",
               source_ref="W9-99:file", at="2029-12-05", mandate="operating")
    m2 = cut_manifest(reg, at="2029-12-31", period_end=True, prior_manifest=m1)
    ok, why = verify_chain([m1, m2])
    assert ok, why
    m2_broken = dict(m2, prior_root="0" * 64)
    ok, why = verify_chain([m1, m2_broken])
    assert not ok and "manifest_hash" in why  # tamper also breaks the self-hash
