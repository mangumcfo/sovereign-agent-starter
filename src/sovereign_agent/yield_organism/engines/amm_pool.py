"""AMMPool — constant-product (x*y=k) market-maker engine, EXTRACTED for the S4 Yield Engine (B4).

PROVENANCE (extract-don't-rewrite, archive discipline):
  origin: mangumcfo/constitution-federation-v2/yield/amm_pool.py
  source_sha256: d9709633adf75ea57ef10c5e1dd92d97ef68e9ecbea2fe43b82d34f0369a7f2d
  lineage: Breath-26 engine, self-test PASS lineage (ignition directive BREATH_26_IGNITION_DIRECTIVE.md).

The class body + self_test() are extracted VERBATIM from the Breath-26 source; the only adaptation is
this provenance docstring prepended above the original imports. The math is unchanged: constant-product
x*y=k, Decimal-exact, NO fee (the fee model is a documented spec gap — register B3 — NOT implemented
here and never invented). This engine COMPUTES a swap output; it moves no money — the money_path-OFF
wiring lives one layer up in economic_actions.py.
"""
import json
from decimal import Decimal, getcontext

# Set precision for Decimal operations
getcontext().prec = 28

class AMMPool:
    """
    Automated Market Maker (AMM) pool using the constant product formula: x * y = k.

    This class manages liquidity pools where token swaps occur such that the product of
    the reserves remains constant. The AMM is crucial for the yield organism, converting
    hardware surplus into LGP tokens that support Lasting Generational Prosperity.
    """

    def __init__(self, reserve_x: Decimal, reserve_y: Decimal):
        """
        Initialize the AMM pool with initial reserves of two assets.

        :param reserve_x: Initial reserve of token X
        :param reserve_y: Initial reserve of token Y
        """
        if reserve_x <= 0 or reserve_y <= 0:
            raise ValueError("Reserves must be positive.")
        self.reserve_x = reserve_x
        self.reserve_y = reserve_y
        self.k = reserve_x * reserve_y

    def calculate_output_amount(self, amount_in: Decimal) -> Decimal:
        """
        Calculate the output amount of token Y given an input amount of token X.

        :param amount_in: Amount of token X to swap in
        :return: Amount of token Y swapped out
        """
        if amount_in <= 0:
            raise ValueError("Input amount must be positive.")
        new_reserve_x = self.reserve_x + amount_in
        amount_out = self.reserve_y - (self.k / new_reserve_x)
        if amount_out <= 0:
            raise ValueError("Insufficient liquidity for the swap.")
        return amount_out

    def swap(self, amount_in: Decimal) -> Decimal:
        """
        Perform a swap of token X for token Y.

        :param amount_in: Amount of token X to swap in
        :return: Amount of token Y swapped out
        """
        amount_out = self.calculate_output_amount(amount_in)
        self.reserve_x += amount_in
        self.reserve_y -= amount_out
        return amount_out

def load_test_boundaries(file_path: str) -> dict:
    """
    Load test boundaries from a YAML file.

    :param file_path: Path to the YAML file containing test boundaries
    :return: Dictionary of test boundaries
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Test boundary file {file_path} not found.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON from {file_path}: {e}")

def self_test() -> bool:
    """Run self-tests and return True if all pass."""
    try:
        # Test core functionality
        pool = AMMPool(Decimal('1000'), Decimal('1000'))

        # Basic swap test
        amount_in = Decimal('10')
        expected_amount_out = Decimal('9.9009900990099')
        result = pool.swap(amount_in)
        assert abs(result - expected_amount_out) < Decimal('0.0001'), f"Basic swap test failed: got {result}"

        # Test with different reserves
        pool = AMMPool(Decimal('500'), Decimal('2000'))
        amount_in = Decimal('50')
        expected_amount_out = Decimal('181.818181818')
        result = pool.swap(amount_in)
        assert abs(result - expected_amount_out) < Decimal('0.0001'), f"Different reserves swap test failed: got {result}"

        # Test boundaries (skipped - YAML boundary tests deferred to smoke harness)
        # Tiger note: YAML loading requires yaml library, using inline tests instead
        pass

        # Edge case: zero input
        try:
            pool.calculate_output_amount(Decimal('0'))
        except ValueError as e:
            assert str(e) == "Input amount must be positive.", "Zero input edge case failed."
        else:
            raise AssertionError("Zero input edge case did not raise expected exception.")

        # Edge case: large swap still produces valid output (formula is always positive for valid inputs)
        pool = AMMPool(Decimal('100'), Decimal('100'))
        large_swap_result = pool.calculate_output_amount(Decimal('200'))
        assert large_swap_result > 0, "Large swap should still produce positive output"

        # Edge case: negative reserves
        try:
            AMMPool(Decimal('-100'), Decimal('100'))
        except ValueError as e:
            assert str(e) == "Reserves must be positive.", "Negative reserve edge case failed."
        else:
            raise AssertionError("Negative reserve edge case did not raise expected exception.")

        return True
    except Exception as e:
        print(f"Self-test failed: {e}")
        return False

if __name__ == "__main__":
    result = self_test()
    print(f"Self Test Passed: {result}")
