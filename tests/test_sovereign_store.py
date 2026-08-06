"""Acceptance tests for Sovereign Data Storage Model (s7_03, S7 Vol 3) — data at rest as governed objects, private/shared
by declared scope, integrity-proven via the sealed P5 Merkle (vendored in-tree, via the _lazy_bp boundary). Retrieval is
deny-by-default, scoped, integrity-checked. No central store, no standing trust across data."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.storage.sovereign_store import store_datum, retrieve_datum, StorageError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _store(reg, owner="nodeA", chunks=(b"secret", b"payload"), visibility="private"):
    return store_datum(reg, owner, list(chunks), visibility=visibility, mandate=owner,
                       author=owner, source_ref=f"store://{owner}", at="2026-08-06")


def test_store_datum_registers_governed_object_with_root(tmp_path):
    reg = _reg(tmp_path)
    d = _store(reg)
    assert d["version_hash"] and d["object_id"].startswith("datum:nodeA:")
    assert d["payload"]["visibility"] == "private" and d["payload"]["root"]  # Merkle integrity root (P5)


def test_store_datum_refuses_empty_or_bad_visibility(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(StorageError):
        store_datum(reg, "", [b"x"], visibility="private", mandate="nodeA", author="nodeA", source_ref="s://1", at="t")
    with pytest.raises(StorageError):
        store_datum(reg, "nodeA", [], visibility="private", mandate="nodeA", author="nodeA", source_ref="s://1", at="t")
    with pytest.raises(StorageError):
        store_datum(reg, "nodeA", [b"x"], visibility="public", mandate="nodeA", author="nodeA", source_ref="s://1", at="t")


def test_retrieve_datum_own_mandate_whole_integrity_verified(tmp_path):
    reg = _reg(tmp_path)
    d = _store(reg, "nodeA", (b"secret", b"payload"))
    res = retrieve_datum(reg, d, [], [b"secret", b"payload"], principal_mandate="nodeA")  # own mandate whole
    assert res["retrieved"] is True and res["integrity"] == "verified"


def test_retrieve_datum_cross_mandate_needs_declared_scope(tmp_path):
    reg = _reg(tmp_path)
    d = _store(reg, "nodeA", (b"secret", b"payload"), visibility="shared")
    # nodeB with no rule -> denied (no standing trust across data)
    with pytest.raises(StorageError):
        retrieve_datum(reg, d, [], [b"secret", b"payload"], principal_mandate="nodeB")
    # nodeA declares a read scope for nodeB -> granted
    rule = SharingRule(d["object_id"], "nodeB", "read")
    res = retrieve_datum(reg, d, [rule], [b"secret", b"payload"], principal_mandate="nodeB")
    assert res["retrieved"] is True


def test_retrieve_datum_denies_tampered_at_rest(tmp_path):
    reg = _reg(tmp_path)
    d = _store(reg, "nodeA", (b"secret", b"payload"))
    with pytest.raises(StorageError):  # presented bytes differ -> Merkle mismatch
        retrieve_datum(reg, d, [], [b"secret", b"ALTERED"], principal_mandate="nodeA")


def test_retrieve_datum_denies_nonexistent(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(StorageError):
        retrieve_datum(reg, {}, [], [b"x"], principal_mandate="nodeA")
