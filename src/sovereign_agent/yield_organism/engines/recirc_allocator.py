"""RecircAllocator — Sri Yantra 70/20/10 yield distribution engine, EXTRACTED for the S4 Yield Engine (B4).

PROVENANCE (extract-don't-rewrite, archive discipline):
  origin: mangumcfo/constitution-federation-v2/yield/recirc_allocator.py
  source_sha256: b6dd6736f42bb13a62c5d1a3b10c5867ee39028917264827565bb8021d38c0be
  lineage: Breath-26 engine, self-test PASS lineage (ignition directive BREATH_26_IGNITION_DIRECTIVE.md).

The class body + self_test() are extracted VERBATIM from the Breath-26 source; the only adaptation is
this provenance docstring prepended above the original imports. The distribution is unchanged: family
0.70 / posterity 0.20 / community 0.10, drawn from the DAO band (allocation is value-conserving —
sum of the three bands equals the total drawn from DAO). This engine COMPUTES an allocation; it moves
no money — the money_path-OFF, receipted wiring lives one layer up in economic_actions.py.
"""
import json
import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class AllocationBand:
    """
    Data class to represent an allocation band in the Sri Yantra 70/20/10 distribution.

    Attributes:
        name (str): Name of the allocation band (e.g., family, posterity, community, DAO).
        percentage (float): Percentage of total allocation for this band.
        current_balance (float): Current balance in this band.
    """
    name: str
    percentage: float
    current_balance: float


class RecircAllocator:
    """
    Class to handle the Sri Yantra 70/20/10 yield distribution among family, posterity,
    community, and DAO with a 21-day smoothing period.

    Attributes:
        bands (List[AllocationBand]): List of allocation bands.
        total_allocation (float): Total amount available for allocation.
        start_date (datetime.date): Start date for the 21-day smoothing period.
        end_date (datetime.date): End date for the 21-day smoothing period.
    """

    def __init__(self, total_allocation: float):
        self.bands = [
            AllocationBand(name="family", percentage=0.70, current_balance=0),
            AllocationBand(name="posterity", percentage=0.20, current_balance=0),
            AllocationBand(name="community", percentage=0.10, current_balance=0),
            AllocationBand(name="DAO", percentage=0.00, current_balance=total_allocation)
        ]
        self.total_allocation = total_allocation
        self.start_date = datetime.date.today()
        self.end_date = self.start_date + datetime.timedelta(days=21)

    def allocate(self) -> None:
        """
        Allocate funds according to the Sri Yantra 70/20/10 distribution.

        Raises:
            ValueError: If there is insufficient balance in the DAO band for allocation.
        """
        try:
            dao_band = next(band for band in self.bands if band.name == "DAO")
            if dao_band.current_balance < self.total_allocation:
                raise ValueError("Insufficient balance in DAO band for allocation.")

            for band in self.bands:
                if band.name != "DAO":
                    amount_to_allocate = self.total_allocation * band.percentage
                    band.current_balance += amount_to_allocate
                    dao_band.current_balance -= amount_to_allocate

        except Exception as e:
            print(f"Error during allocation: {e}")

    def get_balances(self) -> Dict[str, float]:
        """
        Get the current balances of all allocation bands.

        Returns:
            Dict[str, float]: Dictionary with band names as keys and their current balances as values.
        """
        return {band.name: band.current_balance for band in self.bands}

    def get_allocation_details(self) -> List[Dict]:
        """
        Get detailed information about each allocation band.

        Returns:
            List[Dict]: List of dictionaries with details about each allocation band.
        """
        return [json.loads(json.dumps(band.__dict__)) for band in self.bands]

    def __str__(self):
        """
        String representation of the RecircAllocator object, showing current balances.

        Returns:
            str: A formatted string showing the current balance of each band.
        """
        return "\n".join(f"{band.name}: {band.current_balance}" for band in self.bands)


def self_test() -> bool:
    """
    Perform a series of tests to validate the RecircAllocator functionality.

    Returns:
        bool: True if all tests pass, False otherwise.
    """
    try:
        # Test initialization
        allocator = RecircAllocator(total_allocation=1000.0)
        assert len(allocator.bands) == 4

        # Test initial balances
        initial_balances = allocator.get_balances()
        assert initial_balances["family"] == 0 and initial_balances["posterity"] == 0 \
               and initial_balances["community"] == 0 and initial_balances["DAO"] == 1000.0

        # Test allocation
        allocator.allocate()
        allocated_balances = allocator.get_balances()
        assert round(allocated_balances["family"], 2) == 700.0
        assert round(allocated_balances["posterity"], 2) == 200.0
        assert round(allocated_balances["community"], 2) == 100.0
        assert round(allocated_balances["DAO"], 2) == 0.0

        # Test allocation details
        details = allocator.get_allocation_details()
        assert len(details) == 4
        for detail in details:
            if detail['name'] == "family":
                assert round(detail['current_balance'], 2) == 700.0
            elif detail['name'] == "posterity":
                assert round(detail['current_balance'], 2) == 200.0
            elif detail['name'] == "community":
                assert round(detail['current_balance'], 2) == 100.0
            elif detail['name'] == "DAO":
                assert round(detail['current_balance'], 2) == 0.0

        # Test string representation
        str_rep = str(allocator)
        expected_str_rep = "family: 700.0\nposterity: 200.0\ncommunity: 100.0\nDAO: 0.0"
        assert str_rep == expected_str_rep

    except AssertionError as e:
        print(f"Test failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during self-test: {e}")
        return False

    return True


if __name__ == "__main__":
    result = self_test()
    print("Self-test passed:", result)
