import os
import sys
import hashlib
from typing import List, Optional

# Importing layer_1_root crypto primitives
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from sign import sign, ECDSASignature
from verify import verify
from keygen import generate_keypair, KeyPair

# Relative import for Node class in the same directory (layer_2_trunk)
from node import Node

class Proposal:
    """
    Represents a block proposal in the Tendermint-lite consensus system.
    
    Attributes:
        proposer: The node proposing the block.
        block_hash: The hash of the proposed block.
        signature: The ECDSA signature of the proposer on the block hash.
    """

    def __init__(self, proposer: 'Node', block_hash: bytes):
        """
        Initializes a new Proposal instance.

        Args:
            proposer: The node proposing the block.
            block_hash: The hash of the proposed block.
        """
        self.proposer = proposer
        self.block_hash = block_hash
        self.signature = self._sign_block()

    def _sign_block(self) -> ECDSASignature:
        """
        Signs the block hash using the proposer's private key.

        Returns:
            The ECDSA signature of the block hash.
        """
        return sign(self.proposer.private_key, self.block_hash)

    def verify_signature(self) -> bool:
        """
        Verifies the signature of the proposal against the proposer's public key.

        Returns:
            True if the signature is valid, False otherwise.
        """
        return verify(self.proposer.public_key, self.block_hash, self.signature)


class BlockBuilder:
    """
    Handles block building and proposing in the Tendermint-lite consensus system.
    
    Attributes:
        nodes: List of nodes participating in the consensus.
        current_leader: The node elected as the leader for the current round.
    """

    def __init__(self, nodes: List['Node']):
        """
        Initializes a new BlockBuilder instance.

        Args:
            nodes: List of nodes participating in the consensus.
        """
        self.nodes = nodes
        self.current_leader = None

    def elect_leader(self, round_number: int) -> 'Node':
        """
        Elects a leader for a given round based on a simple deterministic rule.

        Args:
            round_number: The current round number.

        Returns:
            The elected leader node.
        """
        # Simple election rule: use modulo to select a leader
        self.current_leader = self.nodes[round_number % len(self.nodes)]
        return self.current_leader

    def build_block(self) -> bytes:
        """
        Builds a new block. This is a placeholder for actual block building logic.

        Returns:
            The hash of the built block.
        """
        # Placeholder: create a dummy block with some data
        block_data = f"Block data for leader {self.current_leader.id} at round {round_number}"
        return hashlib.sha256(block_data.encode()).digest()

    def propose_block(self, block_hash: bytes) -> Proposal:
        """
        Proposes a new block by creating a proposal.

        Args:
            block_hash: The hash of the proposed block.

        Returns:
            A new Proposal instance.
        """
        return Proposal(self.current_leader, block_hash)

    def broadcast_proposal(self, proposal: Proposal):
        """
        Broadcasts the proposal to all nodes in the network.

        Args:
            proposal: The proposal to be broadcasted.
        """
        # Placeholder: simulate broadcasting
        for node in self.nodes:
            node.receive_proposal(proposal)


class Node:
    """
    Represents a node in the Tendermint-lite consensus system.
    
    Attributes:
        id: Unique identifier of the node.
        keypair: Key pair (public and private keys) of the node.
        received_proposals: List of proposals received by the node.
    """

    def __init__(self, node_id: int):
        """
        Initializes a new Node instance.

        Args:
            node_id: Unique identifier of the node.
        """
        self.id = node_id
        self.keypair = generate_keypair()
        self.received_proposals = []

    @property
    def private_key(self) -> bytes:
        """Returns the private key."""
        return self.keypair.private_key

    @property
    def public_key(self) -> bytes:
        """Returns the public key."""
        return self.keypair.public_key

    def receive_proposal(self, proposal: Proposal):
        """
        Receives a proposal from another node.

        Args:
            proposal: The received proposal.
        """
        # Verify the proposal signature
        if proposal.verify_signature():
            self.received_proposals.append(proposal)
            print(f"Node {self.id} received valid proposal.")
        else:
            print(f"Node {self.id} received invalid proposal.")


if __name__ == "__main__":
    # Self-test: create nodes, elect leader, build and propose block
    nodes = [Node(node_id) for node_id in range(4)]
    builder = BlockBuilder(nodes)

    round_number = 1
    leader = builder.elect_leader(round_number)
    print(f"Leader elected for round {round_number}: Node {leader.id}")

    block_hash = builder.build_block()
    proposal = builder.propose_block(block_hash)
    print(f"Proposal created by Leader {proposal.proposer.id} with block hash: {block_hash.hex()}")

    builder.broadcast_proposal(proposal)

    # Check if all nodes received the valid proposal
    for node in nodes:
        assert len(node.received_proposals) == 1, "Node did not receive the expected number of proposals."

    print("passed")

# SEAL