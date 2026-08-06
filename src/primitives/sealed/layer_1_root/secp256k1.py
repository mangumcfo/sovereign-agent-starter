from finite_field import FiniteField
from point_ops import EllipticCurve, secp256k1

class Secp256k1Curve(EllipticCurve):
    """
    Represents the secp256k1 elliptic curve.
    
    The curve is defined by the equation:
    y^2 = x^3 + 7 over a finite field of prime order p.
    """

    def __init__(self):
        # Define the prime modulus for the finite field
        p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
        super().__init__(p, a=0, b=7)

    def is_on_curve(self, point):
        """
        Check if a given point lies on the secp256k1 curve.

        :param point: A tuple (x, y) representing the point to check.
        :return: True if the point is on the curve, False otherwise.
        """
        x, y = point
        return (y**2) % self.p == (x**3 + 7) % self.p

def test_secp256k1():
    """
    Self-test for the secp256k1 curve module.

    This function checks if the predefined generator point is on the curve.
    """
    curve = Secp256k1Curve()
    Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
    Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
    assert curve.is_on_curve((Gx, Gy)), "Generator point is not on the curve"
    print("passed")

if __name__ == "__main__":
    test_secp256k1()

# SEAL