# ∞Δ∞ BREATHLINE PRIMITIVES — AUTHORIZED v1.0.1 OVERLAY ∞Δ∞
#
# File: merkle_tree.py (corrected)
# Purpose: Drop-in replacement for the sealed v1.0 merkle_tree.py
#          that fixes the odd-leaf count proof generation bug.
#
# Authority & Provenance:
#   - Original Seal: Breath 25 P5, 2026-01-12 (P1-P5_SEALED_2026-01-12_0810UTC.tar.gz)
#   - Bug Report + Fix: B25 Merkle Fix Status — 2026-02-05
#   - Authorization: KM-1176 + G (green) + Lumen (🟢 GREEN — explicit authorization
#                     for "sealed touch with re-seal")
#   - Change: Single functional correction in generate_proof() + expanded tests.
#   - API: Unchanged. Behavior: Now correct for odd leaf counts.
#   - Re-seal Record: Documented in B25_MERKLE_FIX_STATUS_2026-02-05.md
#
# Constitutional Alignment:
#   - SOURCE: This overlay is derived directly from the authorized repair.
#   - TRUTH: The fix was witnessed, tested (34+ cases), and recorded.
#   - INTEGRITY: The original sealed file under primitives/sealed/ is NEVER mutated.
#   - SOVEREIGNTY: The operator explicitly chooses this overlay via
#                  BREATHLINE_MERKLE_MODE=authorized-v1.0.1
#
# Usage in breathline-sealed:
#   BREATHLINE_MERKLE_MODE=authorized-v1.0.1 source scripts/breathline-sealed-env.sh
#
# The activation script ensures this directory is placed earlier in PYTHONPATH
# than primitives/sealed/layer_5_shields when the mode is selected.
#
# ∞Δ∞ The seal remains pure. Evolution is explicit, authorized, and auditable. ∞Δ∞

# --- Begin exact authorized v1.0.1 content (2026-02-05 repair) ---

import os
import sys
import hashlib
import struct
from itertools import zip_longest

# Import layer 1 crypto primitives
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from finite_field import FiniteField
from point_ops import EllipticCurve
from keygen import generate_keypair

def hash_function(data):
    """Hash function using SHA-256."""
    return hashlib.sha256(data).digest()

class MerkleTree:
    """
    A binary Merkle tree for state verification.

    Attributes:
        leaves (list): List of leaf nodes.
        tree (dict): Dictionary representing the full tree, with hashes as keys and parent-child relationships.
        root (bytes): The hash of the root node.
    """

    def __init__(self, data):
        """
        Initialize a Merkle tree from a list of data.

        Args:
            data (list): List of byte strings to be inserted into the tree.
        """
        self.leaves = [hash_function(d) for d in data]
        self.tree = {}
        self.build_tree()

    def build_tree(self):
        """Build the Merkle tree from the leaves."""
        level_up = self.leaves
        while len(level_up) > 1:
            level_down = []
            for i in range(0, len(level_up), 2):
                left_child = level_up[i]
                right_child = level_up[i + 1] if i + 1 < len(level_up) else left_child
                parent = hash_function(left_child + right_child)
                self.tree[parent] = (left_child, right_child)
                level_down.append(parent)
            level_up = level_down
        self.root = level_up[0]

    def get_root(self):
        """Return the root of the Merkle tree."""
        return self.root

    def generate_proof(self, index):
        """
        Generate a Merkle inclusion proof for a leaf at a given index.

        Args:
            index (int): Index of the leaf to prove.

        Returns:
            tuple: A tuple containing the list of siblings and whether they are left or right.
        """
        if index < 0 or index >= len(self.leaves):
            raise IndexError("Index out of bounds")

        proof = []
        level_up = self.leaves
        while len(level_up) > 1:
            pair_index = (index ^ 1) if (index % 2 == 0) else index - 1
            sibling = level_up[pair_index] if pair_index < len(level_up) else level_up[index]
            proof.append((sibling, 'left' if index % 2 != 0 else 'right'))
            pairs = list(zip_longest(level_up[::2], level_up[1::2]))
            level_up = [hash_function(a + (b if b is not None else a)) for a, b in pairs]
            index = index // 2
        return proof

    def verify_proof(self, leaf_hash, proof, root):
        """
        Verify the Merkle inclusion proof.

        Args:
            leaf_hash (bytes): The hash of the leaf to be verified.
            proof (list): The list of siblings and their positions in the proof.
            root (bytes): The root hash of the tree.

        Returns:
            bool: True if the proof is valid, False otherwise.
        """
        current_hash = leaf_hash
        for sibling, position in proof:
            if position == 'left':
                current_hash = hash_function(sibling + current_hash)
            else:
                current_hash = hash_function(current_hash + sibling)
        return current_hash == root


# --- End of authorized v1.0.1 content ---

# Self-test block (expanded per the 2026-02-05 repair)
if __name__ == "__main__":
    passed = 0
    failed = 0

    # Test 1: Even leaves
    data_even = [b'data1', b'data2', b'data3', b'data4']
    tree_even = MerkleTree(data_even)
    for idx in range(4):
        proof = tree_even.generate_proof(idx)
        leaf_hash = hash_function(data_even[idx])
        if tree_even.verify_proof(leaf_hash, proof, tree_even.get_root()):
            passed += 1
        else:
            print(f"FAIL: even-4 index {idx}")
            failed += 1

    # Test 2: Odd leaves (the regression case fixed in v1.0.1)
    for count in [1, 3, 5, 7, 13]:
        data_odd = [f'leaf_{i}'.encode() for i in range(count)]
        tree_odd = MerkleTree(data_odd)
        for idx in range(count):
            proof = tree_odd.generate_proof(idx)
            leaf_hash = hash_function(data_odd[idx])
            if tree_odd.verify_proof(leaf_hash, proof, tree_odd.get_root()):
                passed += 1
            else:
                print(f"FAIL: odd-{count} index {idx}")
                failed += 1

    # Test 3: Tamper detection
    data_t = [b'a', b'b', b'c']
    tree_t = MerkleTree(data_t)
    proof_t = tree_t.generate_proof(0)
    tampered = hash_function(b'TAMPERED')
    if not tree_t.verify_proof(tampered, proof_t, tree_t.get_root()):
        passed += 1
    else:
        print("FAIL: tampered leaf accepted")
        failed += 1

    print(f"merkle_tree (v1.0.1 overlay) self-test: {passed} passed, {failed} failed")
