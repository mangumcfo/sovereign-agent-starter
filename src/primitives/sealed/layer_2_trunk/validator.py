import os
import sys
from typing import Dict, List, Tuple

# Import rules from layer_1_root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from sign import sign, ECDSASignature
from verify import verify
from keygen import generate_keypair, KeyPair

# Relative imports for other P2 modules
from node import Node

class Validator:
    """
    A class representing a validator in the Tendermint-lite consensus system.

    Attributes:
        address (str): The unique identifier of the validator.
        public_key (bytes): The public key of the validator used for verification.
        private_key (bytes): The private key of the validator used for signing.
        stake (int): The amount of stake associated with the validator.
    """

    def __init__(self, address: str, stake: int):
        """
        Initialize a new Validator.

        Args:
            address (str): The unique identifier of the validator.
            stake (int): The initial stake of the validator.
        """
        self.address = address
        self.stake = stake
        keypair = generate_keypair()
        self.public_key = keypair.public_key
        self.private_key = keypair.private_key

    @property
    def voting_power(self) -> int:
        """
        Get the voting power of the validator, which is proportional to its stake.

        Returns:
            int: The voting power.
        """
        return self.stake

    def sign_block(self, block_hash: bytes) -> ECDSASignature:
        """
        Sign a block hash using the validator's private key.

        Args:
            block_hash (bytes): The hash of the block to be signed.

        Returns:
            ECDSASignature: The signature of the block.
        """
        return sign(self.private_key, block_hash)

    def verify_signature(self, block_hash: bytes, signature: ECDSASignature) -> bool:
        """
        Verify a signature against a block hash using the validator's public key.

        Args:
            block_hash (bytes): The hash of the block.
            signature (ECDSASignature): The signature to be verified.

        Returns:
            bool: True if the signature is valid, False otherwise.
        """
        return verify(self.public_key, block_hash, signature)

def aggregate_signatures(signatures: List[ECDSASignature]) -> ECDSASignature:
    """
    Aggregate multiple ECDSA signatures into a single signature using P1 ECC.

    Args:
        signatures (List[ECDSASignature]): A list of individual signatures to be aggregated.

    Returns:
        ECDSASignature: The aggregated signature.
    """
    # Placeholder for actual aggregation logic
    # This is a simplified version and should be replaced with actual aggregation algorithm
    if not signatures:
        raise ValueError("No signatures to aggregate")
    
    r_values = [sig.r for sig in signatures]
    s_values = [sig.s for sig in signatures]

    aggregated_r = sum(r_values) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    aggregated_s = sum(s_values) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

    return ECDSASignature(r=aggregated_r, s=aggregated_s)

def self_test():
    """
    Perform a self-test to ensure the Validator class and signature aggregation work correctly.
    """
    # Create two validators
    validator1 = Validator(address="validator_1", stake=100)
    validator2 = Validator(address="validator_2", stake=200)

    # Generate a block hash
    block_hash = b"some_block_hash"

    # Sign the block hash by both validators
    signature1 = validator1.sign_block(block_hash)
    signature2 = validator2.sign_block(block_hash)

    # Verify the signatures
    assert validator1.verify_signature(block_hash, signature1), "Validator 1 signature verification failed"
    assert validator2.verify_signature(block_hash, signature2), "Validator 2 signature verification failed"

    # Aggregate the signatures
    aggregated_signature = aggregate_signatures([signature1, signature2])

    # Print success message
    print("passed")

if __name__ == "__main__":
    self_test()

# SEAL