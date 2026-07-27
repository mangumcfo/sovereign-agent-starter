"""S5-05-E4-1 · E4-4: membership proofs; replay and proof-only agree."""
from sovereign_agent.objects.proofs import (issue_proof, proof_only_check,
                                            replay_root, tree_root, verify_proof)
from sovereign_agent.objects.registry import ObjectRegistry


def _leaves(n=11):
    import hashlib
    return [hashlib.sha256(f"leaf-{i}".encode()).hexdigest() for i in range(n)]


def test_proof_verifies_and_fails_on_single_byte_change():
    leaves = _leaves()
    root = tree_root(leaves)  # also cross-checks the export_packet convention
    for i in (0, 5, len(leaves) - 1):  # first, middle, odd-duplicated last
        path = issue_proof(leaves, i)
        assert verify_proof(leaves[i], path, root)
        flipped = ("0" if leaves[i][0] != "0" else "1") + leaves[i][1:]
        assert not verify_proof(flipped, path, root)  # single byte change fails


def test_replay_and_proof_agree_on_population_root(tmp_path):
    reg = ObjectRegistry(str(tmp_path))
    for i in range(9):
        reg.append(f"asset:A-{i}", {"nbv": i * 1000}, author="d.reyes",
                   source_ref=f"FA-{i}:schedule", at="2029-06-30", mandate="operating")
    stated = replay_root(reg)  # the slow, total check
    for obj in ("asset:A-0", "asset:A-4", "asset:A-8"):
        assert proof_only_check(reg, obj, stated)  # the fast path agrees
    assert not proof_only_check(reg, "asset:A-4", "0" * 64)
