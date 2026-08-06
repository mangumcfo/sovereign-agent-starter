from finite_field import FiniteField
from point_ops import EllipticCurve, secp256k1

def constant_time_cmp(x, y):
    """
    Compares two values in constant time to prevent timing attacks.
    
    Parameters:
    x (int): First value to compare.
    y (int): Second value to compare.
    
    Returns:
    bool: True if x == y, False otherwise.
    """
    result = 0
    for i in range(min(len(x), len(y))):
        result |= ord(x[i]) ^ ord(y[i])
    result |= abs(len(x) - len(y))
    return result == 0

def constant_time_select(choice, a, b):
    """
    Selects between two values in constant time to prevent timing attacks.
    
    Parameters:
    choice (bool): If True, select `a`; otherwise, select `b`.
    a: First value to choose from.
    b: Second value to choose from.
    
    Returns:
    Same type as `a` and `b`: The selected value.
    """
    mask = -int(choice)
    return (mask & a) | (~mask & b)

if __name__ == "__main__":
    # Self-test for constant_time_cmp
    assert constant_time_cmp("test", "test"), "constant_time_cmp failed"
    assert not constant_time_cmp("test", "tesT"), "constant_time_cmp failed"
    assert not constant_time_cmp("short", "longer"), "constant_time_cmp failed"

    # Self-test for constant_time_select
    assert constant_time_select(True, 10, 20) == 10, "constant_time_select failed"
    assert constant_time_select(False, 10, 20) == 20, "constant_time_select failed"
    
    print("passed")

# SEAL