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
            level_up = [hash_function(a + b) for a, b in zip_longest(level_up[::2], level_up[1::2], fillvalue=b'\x00')]
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

# SEAL comment
if __name__ == "__main__":
    # Self-test
    data = [b'data1', b'data2', b'data3', b'data4']
    tree = MerkleTree(data)
    index_to_prove = 1
    proof = tree.generate_proof(index_to_prove)
    leaf_hash = hash_function(data[index_to_prove])
    is_valid = tree.verify_proof(leaf_hash, proof, tree.get_root())
    print("passed" if is_valid else "failed")