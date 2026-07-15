"""VerifiableMemory append-only migration — Universalize Wave §4 (D3 O(n²) kill) + G5 (the riskiest change).

G5 is binding: migrating the legacy whole-file `{version, leaves:[hex…]}` JSON into the append-only NDJSON
leaf log must yield the SAME Merkle root — no root drift, no attestation drift. These pin that equivalence
plus the O(1)-amortized append (the persistence no longer rewrites the whole file)."""
import json

from sovereign_agent.core import VerifiableMemory
from sovereign_agent._lazy_bp import MerkleTree


def _legacy_root(leaves_hex):
    """The pre-wave root: MerkleTree over the leaves, exactly as the old get_root() computed it."""
    return MerkleTree([bytes.fromhex(h) for h in leaves_hex]).get_root()


def test_append_is_append_only_no_whole_file_rewrite(tmp_path):
    """§4: each append adds exactly ONE line to the NDJSON log (O(1) persist) — no whole-file rewrite."""
    vm = VerifiableMemory(tmp_path / "mem.json")
    vm.append(b"a")
    n1 = vm.log_path.read_text().count("\n")
    vm.append(b"b")
    vm.append(b"c")
    n3 = vm.log_path.read_text().count("\n")
    assert n1 == 1 and n3 == 3                 # grew by exactly one line per append
    # the legacy whole-file JSON is NOT written by the new append path
    assert not (tmp_path / "mem.json").exists()


def test_root_is_byte_identical_across_legacy_migration(tmp_path):
    """G5: a legacy JSON of N leaves migrates to the NDJSON log with the SAME root, and a further append
    extends it consistently — no drift."""
    # 1) build a real chain, capture its leaf hexes + root
    seed = VerifiableMemory(tmp_path / "seed.json")  # storage .json → append-only log at seed.ndjson
    for d in (b"alpha", b"beta", b"gamma"):
        seed.append(d)
    leaves_hex = [l.hex() for l in seed.leaves]
    expected_root = _legacy_root(leaves_hex)
    assert seed.get_root() == expected_root

    # 2) materialize those leaves as a LEGACY whole-file JSON (no ndjson alongside)
    legacy = tmp_path / "live.json"
    legacy.write_text(json.dumps({"version": len(leaves_hex), "leaves": leaves_hex}))

    # 3) loading it migrates to the append-only log — root must be byte-identical (G5)
    vm = VerifiableMemory(legacy)
    assert vm.log_path.exists()                          # migrated into the leaf log
    assert vm.get_root() == expected_root                # NO root drift
    assert [l.hex() for l in vm.leaves] == leaves_hex     # same leaves, same order

    # 4) a fresh append extends consistently from the migrated state
    vm.append(b"delta")
    extended = MerkleTree([bytes.fromhex(h) for h in leaves_hex] + [vm.leaves[-1]]).get_root()
    assert vm.get_root() == extended


def test_reload_from_log_preserves_root(tmp_path):
    """A second process opening the same store reads the append-only log and recovers the same root."""
    vm = VerifiableMemory(tmp_path / "m.json")
    for d in (b"x", b"y"):
        vm.append(d)
    root = vm.get_root()
    vm2 = VerifiableMemory(tmp_path / "m.json")
    assert vm2.get_root() == root and len(vm2.leaves) == 2
