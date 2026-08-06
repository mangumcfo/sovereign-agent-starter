import os
import sys
from typing import List, Optional
from node import Node  # Assuming Node is defined in the same directory (layer_2_trunk)

# Importing layer_1_root modules for cryptographic operations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from sign import sign, ECDSASignature
from verify import verify
from keygen import generate_keypair, KeyPair

class Transaction:
    """
    A class representing a transaction in the mempool.
    
    Attributes:
        sender (str): The sender's public key.
        receiver (str): The receiver's public key.
        amount (int): The amount to be transferred.
        signature (ECDSASignature): The signature of the transaction.
    """
    def __init__(self, sender: str, receiver: str, amount: int, signature: ECDSASignature):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature

    def is_valid(self) -> bool:
        """
        Checks if the transaction is valid by verifying its signature.
        
        Returns:
            bool: True if the transaction is valid, False otherwise.
        """
        return verify(self.sender, f"{self.receiver}{self.amount}".encode(), self.signature)

class Mempool:
    """
    A class representing a lightweight transaction mempool for Tendermint-lite consensus.
    
    Attributes:
        transactions (List[Transaction]): The list of transactions in the mempool.
    """
    def __init__(self):
        self.transactions: List[Transaction] = []

    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Adds a valid transaction to the mempool.
        
        Args:
            transaction (Transaction): The transaction to be added.
            
        Returns:
            bool: True if the transaction was successfully added, False otherwise.
        """
        if not transaction.is_valid():
            return False
        self.transactions.append(transaction)
        return True

    def remove_transaction(self, transaction: Transaction) -> bool:
        """
        Removes a transaction from the mempool.
        
        Args:
            transaction (Transaction): The transaction to be removed.
            
        Returns:
            bool: True if the transaction was successfully removed, False otherwise.
        """
        try:
            self.transactions.remove(transaction)
            return True
        except ValueError:
            return False

    def reap_transactions(self) -> List[Transaction]:
        """
        Reaps transactions from the mempool for block building.
        
        Returns:
            List[Transaction]: A list of reaped transactions.
        """
        valid_transactions = [tx for tx in self.transactions if tx.is_valid()]
        self.transactions = []  # Clear the mempool after reaping
        return valid_transactions

# Self-test to ensure everything is working as expected
if __name__ == "__main__":
    # Generate key pairs for sender and receiver
    sender_keypair: KeyPair = generate_keypair()
    receiver_keypair: KeyPair = generate_keypair()

    # Create a transaction from sender to receiver
    amount = 100
    message = f"{receiver_keypair.public_key}{amount}".encode()
    signature = sign(sender_keypair.private_key, message)

    transaction = Transaction(
        sender=sender_keypair.public_key,
        receiver=receiver_keypair.public_key,
        amount=amount,
        signature=signature
    )

    # Create a mempool and add the transaction
    mempool = Mempool()
    if mempool.add_transaction(transaction):
        print("Transaction added successfully.")
    else:
        print("Failed to add transaction.")

    # Reap transactions for block building
    reaped_transactions = mempool.reap_transactions()

    # Verify that the reaped transactions are valid and match the original transaction
    if reaped_transactions and reaped_transactions[0].is_valid() and reaped_transactions[0] == transaction:
        print("passed")
    else:
        print("failed")

# SEAL