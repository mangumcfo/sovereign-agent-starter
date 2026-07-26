"""MintEngine — senior weekly payout engine ($25 floor, eligibility), EXTRACTED for the S4 Yield Engine (B4).

PROVENANCE (extract-don't-rewrite, archive discipline):
  origin: mangumcfo/constitution-federation-v2/yield/payout_engine.py
  source_sha256: 35ddc48a1a25337b205a2035915039a74d4ce0a08ea8cd987e978858e6883174
  lineage: Breath-26 engine, self-test PASS lineage (ignition directive BREATH_26_IGNITION_DIRECTIVE.md).

The class body is extracted VERBATIM from the Breath-26 source. Two minimal adaptations, both noted:
  1. this provenance docstring is prepended above the original imports;
  2. a module-level `self_test()` wrapper is appended (the source ships self_test() as a MintEngine
     METHOD; the wrapper instantiates a MintEngine against a test wallet and runs it, so the engines
     package exposes a uniform module-level self_test() alongside amm_pool / recirc_allocator).
The `execute_payouts()` path here only SIMULATES (prints a transaction log) — it moves no money; the
money_path-OFF, receipted wiring lives one layer up in economic_actions.py.
"""
import os
import json
import hashlib
import datetime
from typing import List, Dict, Union, Optional
from dataclasses import dataclass

@dataclass
class Recipient:
    """
    Data class representing a recipient of the payout.

    Attributes:
        principal_id (str): Unique identifier for the recipient.
        wallet_address (str): XRPL wallet address to which the payout will be sent.
        eligible (bool): Boolean indicating if the recipient is eligible for the payout.
    """
    principal_id: str
    wallet_address: str
    eligible: bool

class MintEngine:
    """
    Class responsible for managing senior weekly payments, ensuring a $25 floor,
    checking eligibility, and handling payouts directly from the treasury.

    Attributes:
        treasury_wallet (str): XRPL address of the treasury.
        payout_amount (float): The minimum amount to be paid out each week.
        recipients (List[Recipient]): List of Recipient objects eligible for payout.
    """

    def __init__(self, treasury_wallet: str, payout_amount: float = 25.0):
        self.treasury_wallet = treasury_wallet
        self.payout_amount = payout_amount
        self.recipients = []

    def add_recipient(self, principal_id: str, wallet_address: str) -> None:
        """
        Adds a new recipient to the list of eligible recipients.

        Args:
            principal_id (str): Unique identifier for the recipient.
            wallet_address (str): XRPL wallet address of the recipient.

        Raises:
            ValueError: If the recipient already exists.
        """
        if any(recipient.principal_id == principal_id for recipient in self.recipients):
            raise ValueError(f"Recipient with principal ID {principal_id} already exists.")

        self.recipients.append(Recipient(principal_id, wallet_address, eligible=True))

    def remove_recipient(self, principal_id: str) -> None:
        """
        Removes a recipient from the list of recipients.

        Args:
            principal_id (str): Unique identifier for the recipient to be removed.

        Raises:
            ValueError: If the recipient does not exist.
        """
        self.recipients = [recipient for recipient in self.recipients if recipient.principal_id != principal_id]

    def set_eligibility(self, principal_id: str, eligible: bool) -> None:
        """
        Sets the eligibility status of a recipient.

        Args:
            principal_id (str): Unique identifier for the recipient.
            eligible (bool): Boolean indicating new eligibility status.

        Raises:
            ValueError: If the recipient does not exist.
        """
        for recipient in self.recipients:
            if recipient.principal_id == principal_id:
                recipient.eligible = eligible
                return

        raise ValueError(f"Recipient with principal ID {principal_id} not found.")

    def generate_payouts(self) -> List[Dict[str, Union[str, float]]]:
        """
        Generates a list of payouts to be made to eligible recipients.

        Returns:
            List[Dict[str, Union[str, float]]]: List of dictionaries containing recipient details and payout amount.
        """
        payouts = []
        for recipient in self.recipients:
            if recipient.eligible:
                payouts.append({
                    "principal_id": recipient.principal_id,
                    "wallet_address": recipient.wallet_address,
                    "amount": self.payout_amount
                })

        return payouts

    def execute_payouts(self) -> None:
        """
        Executes the payout process, simulating sending funds to eligible recipients.

        Raises:
            Exception: If an error occurs during the execution of a payout.
        """
        payouts = self.generate_payouts()
        for payout in payouts:
            try:
                # Simulate transaction
                print(f"Sending {payout['amount']} to {payout['wallet_address']} (Principal ID: {payout['principal_id']})")

                # Log transaction details
                log_entry = {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "transaction_id": self._generate_transaction_id(payout),
                    **payout
                }
                print(f"Transaction Log: {log_entry}")

            except Exception as e:
                raise Exception(f"Failed to execute payout for recipient ID {payout['principal_id']}: {e}")

    def _generate_transaction_id(self, payout: Dict[str, Union[str, float]]) -> str:
        """
        Generates a unique transaction ID based on payout details.

        Args:
            payout (Dict[str, Union[str, float]]): Dictionary containing recipient details and payout amount.

        Returns:
            str: Unique transaction ID.
        """
        data_str = json.dumps(payout, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def self_test(self) -> bool:
        """
        Runs a self-test to ensure the MintEngine is functioning correctly.

        Returns:
            bool: True if all tests pass, False otherwise.
        """
        try:
            # Add recipients
            self.add_recipient("001", "rGgR41k9mg8Ac2g6Z61bmbL1AUfGQq9491")
            self.add_recipient("002", "rnFLEFfk13YhtFPYL6LdYpdL329CJtawRh")

            # Set eligibility
            self.set_eligibility("001", True)
            self.set_eligibility("002", False)

            # Generate and execute payouts
            payouts = self.generate_payouts()
            assert len(payouts) == 1, "Payout generation failed."
            assert payouts[0]["principal_id"] == "001", "Incorrect recipient in payouts."

            self.execute_payouts()

            print("Self-test passed.")
            return True

        except Exception as e:
            print(f"Self-test failed: {e}")
            return False


def self_test() -> bool:
    """Module-level wrapper (adaptation #2) — runs MintEngine.self_test() on a test treasury wallet so
    the engines package exposes a uniform module-level self_test(). The underlying assertions are the
    Breath-26 source's own (verbatim)."""
    return MintEngine(treasury_wallet="rTESTtreasuryWalletForSelfTestOnly000000").self_test()


# Example usage
if __name__ == "__main__":
    mint_engine = MintEngine(treasury_wallet="rhpcC14oguHwXu7eGciTcbrVRh8AzAAkkh")
    mint_engine.self_test()
