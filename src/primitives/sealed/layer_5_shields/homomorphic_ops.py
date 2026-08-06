import os
import sys
import secrets
from hashlib import sha256
from struct import pack, unpack

# Import from layer_1_root as per import rules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from finite_field import FiniteField
from point_ops import EllipticCurve
from keygen import generate_keypair

class PaillierPublicKey:
    def __init__(self, n):
        self.n = n
        self.nsquare = n * n

class PaillierPrivateKey:
    def __init__(self, p, q, public_key):
        self.p = p
        self.q = q
        self.public_key = public_key
        self.lam = (p - 1) * (q - 1)
        self.mu = pow(self.lam, -1, public_key.n)

def generate_paillier_keys(bit_length=512):
    """
    Generate a Paillier keypair.

    :param bit_length: The bit length of the prime numbers p and q.
    :return: A tuple containing the private key and the public key.
    """
    p = secrets.randbits(bit_length)
    q = secrets.randbits(bit_length)
    while not is_prime(p):
        p = secrets.randbits(bit_length)
    while not is_prime(q) or p == q:
        q = secrets.randbits(bit_length)

    n = p * q
    public_key = PaillierPublicKey(n)
    private_key = PaillierPrivateKey(p, q, public_key)
    return private_key, public_key

def is_prime(num):
    """
    Check if a number is prime using a simple probabilistic test.

    :param num: The number to check.
    :return: True if the number is likely prime, False otherwise.
    """
    if num < 2:
        return False
    for _ in range(10):  # Number of iterations for Miller-Rabin primality test
        a = secrets.randbelow(num - 3) + 2
        if pow(a, num - 1, num) != 1:
            return False
    return True

def encrypt(public_key, plaintext):
    """
    Encrypt a plaintext using the Paillier public key.

    :param public_key: The Paillier public key.
    :param plaintext: The plaintext to encrypt (an integer).
    :return: The ciphertext as an integer.
    """
    r = secrets.randbelow(public_key.n)
    while gcd(r, public_key.n) != 1:
        r = secrets.randbelow(public_key.n)

    n = public_key.n
    g = n + 1
    ciphertext = pow(g, plaintext, public_key.nsquare) * pow(r, n, public_key.nsquare) % public_key.nsquare
    return ciphertext

def decrypt(private_key, ciphertext):
    """
    Decrypt a ciphertext using the Paillier private key.

    :param private_key: The Paillier private key.
    :param ciphertext: The ciphertext to decrypt (an integer).
    :return: The plaintext as an integer.
    """
    n = private_key.public_key.n
    nsquare = private_key.public_key.nsquare
    lam = private_key.lam

    u = pow(ciphertext, lam, nsquare)
    L_u = (u - 1) // n
    plaintext = L_u * private_key.mu % n
    return plaintext

def add(public_key, ciphertext1, ciphertext2):
    """
    Add two Paillier ciphertexts.

    :param public_key: The Paillier public key.
    :param ciphertext1: The first ciphertext (an integer).
    :param ciphertext2: The second ciphertext (an integer).
    :return: The resulting ciphertext after addition.
    """
    return ciphertext1 * ciphertext2 % public_key.nsquare

def gcd(a, b):
    """
    Compute the greatest common divisor of a and b.

    :param a: First number.
    :param b: Second number.
    :return: The greatest common divisor of a and b.
    """
    while b != 0:
        a, b = b, a % b
    return a

def self_test():
    """
    Perform a self-test to verify the correctness of the Paillier operations.

    :return: None
    """
    private_key, public_key = generate_paillier_keys()
    plaintext1 = 42
    plaintext2 = 7

    ciphertext1 = encrypt(public_key, plaintext1)
    ciphertext2 = encrypt(public_key, plaintext2)

    decrypted1 = decrypt(private_key, ciphertext1)
    decrypted2 = decrypt(private_key, ciphertext2)

    assert decrypted1 == plaintext1, "Decryption failed for first plaintext"
    assert decrypted2 == plaintext2, "Decryption failed for second plaintext"

    added_ciphertext = add(public_key, ciphertext1, ciphertext2)
    added_plaintext = decrypt(private_key, added_ciphertext)

    assert (plaintext1 + plaintext2) % public_key.n == added_plaintext, "Addition failed"

    print("passed")

if __name__ == "__main__":
    self_test()
# SEAL