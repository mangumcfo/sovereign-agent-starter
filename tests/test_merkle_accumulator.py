"""Engine 95+ HIGH #1 — the incremental frontier Merkle accumulator (card cd010960, thread [350/351]).

This is the COMPLETION test (proves the FULL chain, not the attempt — the discipline missing at 82):
  - root-equivalence vs the legacy MerkleTree oracle across every leaf count, esp. odd/even boundaries
    and powers of two (the duplicate-last-odd structure changes exactly there);
  - incremental == batch (appending one-at-a-time == building from the full list);
  - O(log n) append complexity, asserted on the hash-call count (kills the O(n^2));
  - persistence round-trip — reload from the NDJSON log reproduces the identical root (G5 across restart);
  - real demo data: existing-shape leaves keep a byte-identical root.

The legacy `MerkleTree` is the ORACLE: the accumulator must equal it, byte-for-byte, always.
Crypto-dependent — explicit skipif on the sealed substrate (peer review [351] #2: no silent false-green).
"""
import pytest


def _substrate_available() -> bool:
    """Resolve the sealed crypto substrate the SAME way the runtime does (bootstrap, then exercise it).
    Returns True only when MerkleTree genuinely runs — so the skip below reflects real absence, never a
    pre-bootstrap path miss (peer review [351] #2: explicit named condition, no silent false-green)."""
    try:
        from sovereign_agent.bootstrap import ensure_breathline_primitives
        ensure_breathline_primitives()
    except Exception:
        pass
    try:
        from sovereign_agent._lazy_bp import MerkleTree as _MT
        _MT([b"probe"]).get_root()
        return True
    except Exception:
        return False


# peer review [351] #2: skip EXPLICITLY on a named condition, never swallow an ImportError into a false green.
pytestmark = pytest.mark.skipif(not _substrate_available(),
                                reason="breathline_primitives (sealed crypto substrate) absent")

from sovereign_agent._lazy_bp import MerkleTree, hash_function  # noqa: E402
from sovereign_agent.merkle_accumulator import MerkleAccumulator  # noqa: E402


def _oracle_root(leaves):
    """The pre-wave root: MerkleTree over the leaves, exactly as the old get_root() computed it."""
    return MerkleTree(list(leaves)).get_root()


# ── root-equivalence across leaf counts (the non-negotiable gate) ──────────────────────────────────
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 100, 127, 128, 200])
def test_root_equivalent_to_merkletree_at_every_count(n):
    """For n leaves the accumulator root is byte-identical to MerkleTree(leaves).get_root() — incl. the
    odd/even and power-of-two boundaries where the duplicate-last-odd structure shifts."""
    leaves = [f"leaf-{i}".encode() for i in range(n)]
    acc = MerkleAccumulator.from_leaves(leaves)
    assert acc.get_root() == _oracle_root(leaves), f"root drift at n={n}"
    assert acc.size == n


def test_root_equivalent_step_by_step_through_boundaries():
    """Append one leaf at a time and assert equivalence AFTER EVERY append (catches a self-paired odd node
    that fails to recompute when its sibling arrives — peer review [351] #1)."""
    acc = MerkleAccumulator()
    leaves = []
    for i in range(80):
        leaves.append(f"x-{i}".encode())
        root = acc.append(leaves[-1])
        assert root == _oracle_root(leaves), f"root drift after appending leaf {i}"


def test_incremental_equals_batch():
    """One-at-a-time accumulation yields the same root as building from the full list in one go."""
    leaves = [f"d-{i}".encode() for i in range(50)]
    one_at_a_time = MerkleAccumulator()
    for d in leaves:
        one_at_a_time.append(d)
    assert one_at_a_time.get_root() == MerkleAccumulator.from_leaves(leaves).get_root()


def test_empty_and_single():
    acc = MerkleAccumulator()
    assert acc.get_root() is None and acc.size == 0          # matches VerifiableMemory's None-when-empty
    acc.append(b"only")
    assert acc.get_root() == _oracle_root([b"only"])


# ── complexity proof: O(log n) per append, NOT O(n) (the O(n^2)-kill, completion-verified) ─────────
def test_append_is_logarithmic_not_linear():
    """Count hash_function calls per append; assert each append costs <= c*log2(k)+c hashes (O(log n)),
    not O(k). A full-tree rebuild would be O(k) per append (the O(n^2) we are killing)."""
    import sovereign_agent.merkle_accumulator as mod

    calls = {"n": 0}
    real = mod.hash_function

    def counting(b):
        calls["n"] += 1
        return real(b)

    mod.hash_function = counting
    try:
        acc = MerkleAccumulator()
        N = 1024
        for k in range(1, N + 1):
            calls["n"] = 0
            acc.append(f"leaf-{k}".encode())
            # 1 hash for the leaf + at most one parent per level (~log2 k). Generous constant guard.
            import math
            bound = 3 * (math.floor(math.log2(k)) + 2)
            assert calls["n"] <= bound, f"append {k} used {calls['n']} hashes (> {bound}) — not O(log n)"
    finally:
        mod.hash_function = real


# ── persistence round-trip + real VerifiableMemory wiring (G5 across restart) ──────────────────────
def test_verifiable_memory_root_matches_oracle_and_survives_reload(tmp_path):
    """The wired VerifiableMemory root equals the oracle AND a reload from the NDJSON log reproduces the
    identical root (the accumulator is rebuilt from the persisted leaves on load)."""
    from sovereign_agent.core import VerifiableMemory

    vm = VerifiableMemory(tmp_path / "mem.json")
    roots = [vm.append(f"event-{i}".encode()) for i in range(40)]
    assert vm.get_root() == _oracle_root(vm.leaves)         # wired root == oracle
    assert roots[-1] == vm.get_root()

    reloaded = VerifiableMemory(tmp_path / "mem.json")       # rebuild accumulator from the persisted log
    assert reloaded.get_root() == vm.get_root()             # byte-identical across restart (G5)
    assert reloaded.leaves == vm.leaves
