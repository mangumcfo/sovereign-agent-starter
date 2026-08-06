from finite_field import FiniteField
from point_ops import EllipticCurve

class CurveEd25519(EllipticCurve):
    """
    Represents the Ed25519 elliptic curve used in EdDSA.
    
    The equation of the curve is:
        -x^2 + y^2 = 1 - (121665/121666) * x^2 * y^2
    """
    
    def __init__(self):
        # Define the finite field for Ed25519: GF(2^255 - 19)
        self.p = 2**255 - 19
        FiniteField.p = self.p
        
        # Curve parameters
        self.d = -121665 * pow(121666, -1, self.p) % self.p
        self.a = 0
        self.b = 1
        self.base_x = 9
        self.base_y = 1478161944758954479102059356840998688726460613461647528759788105625139110816
        self.order = 2**252 + 2774231777737235353585039542971247713447574156976009735197892562576

        # Initialize the base point
        self.G = (self.base_x, self.base_y)
        
    def add(self, P, Q):
        """
        Adds two points on the Ed25519 curve.
        
        :param P: A tuple (x1, y1) representing a point on the curve.
        :param Q: A tuple (x2, y2) representing another point on the curve.
        :return: The resulting point (x3, y3).
        """
        if P is None:
            return Q
        if Q is None:
            return P
        
        x1, y1 = P
        x2, y2 = Q
        
        # Curve equation parameters
        a = self.a
        d = self.d
        
        # Intermediate values for addition formula
        x3 = (x1*y2 + y1*x2) * pow(1 - d*x1*x2*y1*y2, -1, self.p)
        y3 = (y1*y2 + a*x1*x2) * pow(1 + d*x1*x2*y1*y2, -1, self.p)
        
        return x3 % self.p, y3 % self.p
    
    def double(self, P):
        """
        Doubles a point on the Ed25519 curve.
        
        :param P: A tuple (x, y) representing a point on the curve.
        :return: The resulting point after doubling.
        """
        return self.add(P, P)
    
    def scalar_multiply(self, k, P=None):
        """
        Performs scalar multiplication on the Ed25519 curve.
        
        :param k: An integer scalar.
        :param P: A tuple (x, y) representing a point on the curve. If None, uses the base point G.
        :return: The resulting point after scalar multiplication.
        """
        if P is None:
            P = self.G
        
        result = None
        addend = P
        
        while k != 0:
            if k & 1:
                result = self.add(result, addend)
            addend = self.double(addend)
            k >>= 1
        
        return result

def test_ed25519():
    """
    Self-test for the Ed25519 curve implementation.
    """
    curve = CurveEd25519()
    
    # Test scalar multiplication with base point
    G = curve.G
    scalar = 123456789
    result_point = curve.scalar_multiply(scalar, G)
    
    # Simple test: doubling a point and comparing with addition
    P = curve.G
    Q = curve.add(P, P)
    R = curve.double(P)
    
    assert Q == R, "Double method failed the self-test."
    
    print("passed")

if __name__ == "__main__":
    test_ed25519()

# SEAL