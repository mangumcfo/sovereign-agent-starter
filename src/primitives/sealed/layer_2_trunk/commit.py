import os
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Import rules from layer_1_root for crypto operations
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from sign import sign, ECDSASignature
from verify import verify
from keygen import generate_keypair, KeyPair

# Relative import for other P2 modules
from node import Node

@dataclass
class Vote:
    """
    Represents a vote in the Tendermint-lite consensus process.
    
    Attributes:
        validator_id (str): Identifier of the validator.
        round (int): The round number of the vote.
        height (int): The block height for which this vote is cast.
        block_hash (bytes): Hash of the proposed block.
        signature (ECDSASignature): Signature of the vote by the validator.
    """
    validator_id: str
    round: int
    height: int
    block_hash: bytes
    signature: ECDSASignature

class CommitPipeline:
    """
    Implements the commit pipeline in a Tendermint-lite consensus system.
    
    Attributes:
        validators (Dict[str, KeyPair]): Dictionary of validators with their key pairs.
        votes_prevote (List[Vote]): List of prevote messages received from validators.
        votes_precommit (List[Vote]): List of precommit messages received from validators.
        threshold (int): The 2/3 threshold for consensus.
    """
    
    def __init__(self, validators: Dict[str, KeyPair]):
        self.validators = validators
        self.votes_prevote = []
        self.votes_precommit = []
        self.threshold = len(validators) * 2 // 3 + 1

    def add_vote(self, vote: Vote, phase: str):
        """
        Adds a vote to the respective list based on the phase (prevote or precommit).
        
        Args:
            vote (Vote): The vote message.
            phase (str): The phase of the vote ('prevote' or 'precommit').
        """
        if phase == 'prevote':
            self.votes_prevote.append(vote)
        elif phase == 'precommit':
            self.votes_precommit.append(vote)

    def check_votes(self, votes: List[Vote], block_hash: bytes) -> bool:
        """
        Checks if the number of valid votes for a specific block hash meets the 2/3 threshold.
        
        Args:
            votes (List[Vote]): The list of votes to check.
            block_hash (bytes): The block hash being voted on.
            
        Returns:
            bool: True if the threshold is met, False otherwise.
        """
        valid_votes = 0
        for vote in votes:
            keypair = self.validators.get(vote.validator_id)
            if keypair and verify(keypair.public_key, vote.block_hash, vote.signature):
                if vote.block_hash == block_hash:
                    valid_votes += 1
                    if valid_votes >= self.threshold:
                        return True
        return False

    def prevote_to_precommit(self, block_hash: bytes) -> bool:
        """
        Transitions from the prevote phase to the precommit phase.
        
        Args:
            block_hash (bytes): The block hash that validators have prevoted for.
            
        Returns:
            bool: True if the transition is successful, False otherwise.
        """
        return self.check_votes(self.votes_prevote, block_hash)

    def precommit_to_commit(self, block_hash: bytes) -> bool:
        """
        Transitions from the precommit phase to the commit state.
        
        Args:
            block_hash (bytes): The block hash that validators have precommitted for.
            
        Returns:
            bool: True if the transition is successful, False otherwise.
        """
        return self.check_votes(self.votes_precommit, block_hash)

    def run_commit_pipeline(self, proposed_block_hash: bytes) -> Optional[str]:
        """
        Runs the full commit pipeline from prevote to commit.
        
        Args:
            proposed_block_hash (bytes): The hash of the proposed block.
            
        Returns:
            Optional[str]: 'committed' if the block is committed, None otherwise.
        """
        # Simulate receiving enough valid prevotes for a block
        for validator_id, keypair in self.validators.items():
            prevote_signature = sign(keypair.private_key, proposed_block_hash)
            prevote = Vote(validator_id, 0, 1, proposed_block_hash, prevote_signature)
            self.add_vote(prevote, 'prevote')

        # Simulate receiving enough valid precommits for a block
        if self.prevote_to_precommit(proposed_block_hash):
            for validator_id, keypair in self.validators.items():
                precommit_signature = sign(keypair.private_key, proposed_block_hash)
                precommit = Vote(validator_id, 0, 1, proposed_block_hash, precommit_signature)
                self.add_vote(precommit, 'precommit')

        # Check if the block can be committed
        if self.precommit_to_commit(proposed_block_hash):
            return 'committed'
        return None

if __name__ == "__main__":
    # Generate keypairs for validators
    num_validators = 4
    validators = {f'validator_{i}': generate_keypair() for i in range(num_validators)}

    # Create a commit pipeline instance with the generated validators
    commit_pipeline = CommitPipeline(validators)

    # Simulate a proposed block hash
    proposed_block_hash = b'\x01\x02\x03'

    # Run the commit pipeline
    result = commit_pipeline.run_commit_pipeline(proposed_block_hash)
    
    if result == 'committed':
        print("passed")
    else:
        print("failed")

# SEAL