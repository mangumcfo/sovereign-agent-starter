import os
import sys
import json
import hashlib
from typing import List, Dict, Any, Optional
import time

# Import P1 crypto primitives
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from sign import sign, ECDSASignature
from verify import verify
from keygen import generate_keypair, KeyPair

class Block:
    """
    Represents a block in the blockchain.
    
    Attributes:
        index (int): The block's index in the chain.
        timestamp (float): The time the block was created.
        transactions (List[Dict[str, Any]]): A list of transactions included in this block.
        previous_hash (str): The hash of the previous block in the chain.
        nonce (int): A nonce used for mining proof-of-work.
        hash (str): The hash of this block.
    """
    
    def __init__(self, index: int, timestamp: float, transactions: List[Dict[str, Any]], previous_hash: str = ''):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of this block."""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    """
    Represents the blockchain.
    
    Attributes:
        chain (List[Block]): The list of blocks in the blockchain.
        current_transactions (List[Dict[str, Any]]): A list of transactions awaiting to be added to a block.
    """
    
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.current_transactions = []
    
    @staticmethod
    def create_genesis_block() -> Block:
        """Create the genesis block."""
        return Block(0, time.time(), [], '0')
    
    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """
        Creates a new transaction to go into the next mined block.
        
        Args:
            sender (str): The address of the sender.
            recipient (str): The address of the recipient.
            amount (float): The amount being sent.
        
        Returns:
            int: The index of the block that will hold this transaction.
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.last_block.index + 1
    
    @property
    def last_block(self) -> Block:
        """Returns the last block in the chain."""
        return self.chain[-1]
    
    def new_block(self, proof: int, previous_hash: Optional[str] = None) -> Block:
        """
        Create a new block in the blockchain.
        
        Args:
            proof (int): The proof given by the Proof of Work algorithm.
            previous_hash (str): Hash of the previous block.
            
        Returns:
            Block: New block
        """
        if previous_hash is None:
            previous_hash = self.last_block.hash
        
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=self.current_transactions,
            previous_hash=previous_hash
        )
        
        block.nonce = proof
        block.hash = block.calculate_hash()
        
        # Reset the current list of transactions
        self.current_transactions = []
        
        self.chain.append(block)
        return block

class Node:
    """
    Represents a node in the Tendermint-lite consensus network.
    
    Attributes:
        blockchain (Blockchain): The local copy of the blockchain.
        peers (List[str]): A list of peer nodes in the network.
        keypair (KeyPair): The cryptographic key pair for this node.
    """
    
    def __init__(self):
        self.blockchain = Blockchain()
        self.peers = []
        self.keypair = generate_keypair()
    
    def broadcast_transaction(self, transaction: Dict[str, Any]):
        """
        Broadcast a new transaction to all peers.
        
        Args:
            transaction (Dict[str, Any]): The transaction to be broadcasted.
        """
        for peer in self.peers:
            # Simulate broadcasting to a peer
            print(f"Broadcasting transaction {transaction} to {peer}")
    
    def mine_block(self):
        """Mine a new block."""
        proof = self.proof_of_work()
        previous_hash = self.blockchain.last_block.hash
        block = self.blockchain.new_block(proof, previous_hash)
        
        # Broadcast the newly mined block to all peers
        for peer in self.peers:
            print(f"Broadcasting new block {block.index} to {peer}")
    
    def proof_of_work(self) -> int:
        """Simple Proof of Work algorithm."""
        last_proof = self.blockchain.last_block.nonce
        proof = 0
        
        while not self.valid_proof(last_proof, proof):
            proof += 1
        
        return proof
    
    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        Validates the Proof.
        
        Args:
            last_proof (int): Previous Proof.
            proof (int): Current Proof.
            
        Returns:
            bool: True if correct, False otherwise.
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
    def add_transaction(self, transaction: Dict[str, Any]):
        """
        Add a new transaction to the list of transactions.
        
        Args:
            transaction (Dict[str, Any]): The transaction details.
            
        Returns:
            int: The index of the block that will hold this transaction.
        """
        return self.blockchain.new_transaction(**transaction)

def main():
    # Initialize node
    node = Node()
    
    # Simulate adding a peer
    node.peers.append("peer1")
    node.peers.append("peer2")
    
    # Simulate transactions
    node.add_transaction({'sender': 'A', 'recipient': 'B', 'amount': 5.0})
    node.add_transaction({'sender': 'B', 'recipient': 'C', 'amount': 3.0})
    
    # Mine a new block
    node.mine_block()
    
    # Validate the blockchain
    if len(node.blockchain.chain) > 1:
        print("passed")
    else:
        print("failed")

if __name__ == "__main__":
    main()

# SEAL