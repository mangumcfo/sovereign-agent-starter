"""Incremental frontier Merkle accumulator — Engine 95+ HIGH #1 (card cd010960, thread [350/351]).

Reproduces ``breathline_primitives.MerkleTree``'s flat, duplicate-last-odd tree INCREMENTALLY:
appending a leaf recomputes only the right frontier (O(log n) hashes) and never rebuilds from
genesis. The root is byte-identical to ``MerkleTree(data).get_root()`` for every leaf count — the
non-negotiable equivalence gate (no attestation drift, G5). Proven in tests/test_merkle_accumulator.py.

Shape (the peer's leaf_log -> segment_root -> checkpoint_root -> global_commitment):
  _levels[0]      = leaf_log  (hash_function(leaf) for each appended leaf — MerkleTree re-hashes inputs)
  _levels[k<top]  = interior levels; complete left subtrees (index < frontier) are frozen, never recomputed
  _levels[-1][0]  = global_commitment (the root)

Equivalence-critical details the accumulator MUST reproduce (both are silent-drift traps):
  1. MerkleTree re-hashes each input:  self.leaves = [hash_function(d) for d in data]  -> we hash on append.
  2. Duplicate-last-odd pairing:  a lone right node is hashed with ITSELF -> parent = hash(x + x).

Refinement (peer review [351] #1): recompute the FULL right frontier each append, INCLUDING self-paired odd
nodes — freeze only complete left subtrees. A node that is currently self-paired (odd count) is NOT
frozen; when its sibling arrives the parent is recomputed from hash(x+x) to hash(x+y). The odd/even
root-equivalence test proves this.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from ._lazy_bp import hash_function


class MerkleAccumulator:
    """O(log n)-per-append frontier accumulator, root-equivalent to the flat MerkleTree."""

    def __init__(self) -> None:
        # _levels[0] = hashed leaves; _levels[k] = parent level k. Mirrors MerkleTree's level structure.
        self._levels: List[List[bytes]] = [[]]

    @property
    def size(self) -> int:
        """Number of leaves accumulated."""
        return len(self._levels[0])

    def append(self, data: bytes) -> Optional[bytes]:
        """Append one leaf (hashed exactly as MerkleTree does) and update the right frontier in O(log n).

        Only the single rightmost parent at each level can change when a leaf is appended; every node to
        its left is a complete, frozen subtree and is never touched. Returns the new root.
        """
        self._levels[0].append(hash_function(data))
        k = 0
        while len(self._levels[k]) > 1:
            level = self._levels[k]
            p = (len(level) - 1) // 2  # the ONLY parent index the new leaf can affect (the right frontier)
            left = level[2 * p]
            # Duplicate-last-odd: a lone right node is hashed with itself (hash(x+x)), exactly as MerkleTree.
            right = level[2 * p + 1] if (2 * p + 1) < len(level) else left
            parent = hash_function(left + right)
            if k + 1 == len(self._levels):
                self._levels.append([])
            up = self._levels[k + 1]
            if p == len(up):
                up.append(parent)        # new frontier parent
            else:
                up[p] = parent           # recompute a previously self-paired parent now properly paired
            k += 1
        return self.get_root()

    def get_root(self) -> Optional[bytes]:
        """Return the current root in O(1). None for an empty accumulator (matches VerifiableMemory)."""
        if not self._levels[0]:
            return None
        return self._levels[-1][0]

    @classmethod
    def from_leaves(cls, data_iter: Iterable[bytes]) -> "MerkleAccumulator":
        """Build an accumulator by appending each leaf in order (used on load / for the oracle test)."""
        acc = cls()
        for d in data_iter:
            acc.append(d)
        return acc
