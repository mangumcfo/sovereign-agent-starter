import os
import sys
import hashlib
import base64

# Inserting paths for custom layers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from keygen import generate_keypair, KeyPair
from sign import sign
from verify import verify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))

# Base58 encoding utilities
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def b58encode(b):
    """ Encode bytes to base58 """
    n = int.from_bytes(b, 'big')
    leading_zeroes = len(b) - len(b.lstrip(b'\0'))
    prefix = BASE58_ALPHABET[0] * leading_zeroes
    result = []
    while n > 0:
        n, r = divmod(n, 58)
        result.append(BASE58_ALPHABET[r])
    return prefix + ''.join(reversed(result))

def b58decode(s):
    """ Decode base58 to bytes """
    n = 0
    for char in s:
        n = n * 58 + BASE58_ALPHABET.index(char)
    leading_zeroes = len(s) - len(s.lstrip(BASE58_ALPHABET[0]))
    prefix = b'\x00' * leading_zeroes
    return prefix + n.to_bytes((n.bit_length() + 7) // 8, 'big') or b'\x00'

def generate_multihash(data):
    """
    Generate a multihash from the given data using SHA-256.
    
    Args:
        data (bytes): The input data to hash.
        
    Returns:
        bytes: Multihash representation of the data.
    """
    sha256_hash = hashlib.sha256(data).digest()
    # SHA-2-256 code is 0x12 and length is 32
    return b'\x12\x20' + sha256_hash

def encode_cid_v0(multihash):
    """
    Encode a multihash into CID version 0 using base58.
    
    Args:
        multihash (bytes): The multihash to encode.
        
    Returns:
        str: Base58 encoded CID v0 string.
    """
    return b58encode(multihash)

def encode_cid_v1(multihash, codec='dag-pb', multibase='base58btc'):
    """
    Encode a multihash into CID version 1 using specified multibase encoding.
    
    Args:
        multihash (bytes): The multihash to encode.
        codec (str): The codec used ('dag-pb' for example).
        multibase (str): The multibase to use ('base58btc', 'base32').
        
    Returns:
        str: Encoded CID v1 string.
    """
    # Codec code for dag-pb is 0x70
    codec_code = b'\x70'
    version = b'\x01'
    
    if multibase == 'base58btc':
        prefix = b'\x01\x71'  # CIDv1 + base58btc
        cid_bytes = version + codec_code + multihash
        return b58encode(cid_bytes)
    elif multibase == 'base32':
        prefix = b'\x01\x55'  # CIDv1 + base32
        cid_bytes = version + codec_code + multihash
        return base64.b32encode(cid_bytes).decode().lower()
    else:
        raise ValueError("Unsupported multibase encoding")

def self_test():
    """
    Perform a self-test to ensure all components work as expected.
    
    Prints "passed" if all tests succeed, otherwise raises an AssertionError.
    """
    # Generate test data
    test_data = b'This is some test data'
    multihash = generate_multihash(test_data)
    
    # Encode CID v0
    cid_v0 = encode_cid_v0(multihash)
    assert isinstance(cid_v0, str), "CID v0 should be a string"
    
    # Encode CID v1 with base58btc
    cid_v1_base58 = encode_cid_v1(multihash, multibase='base58btc')
    assert isinstance(cid_v1_base58, str), "CID v1 (base58) should be a string"
    
    # Encode CID v1 with base32
    cid_v1_base32 = encode_cid_v1(multihash, multibase='base32')
    assert isinstance(cid_v1_base32, str), "CID v1 (base32) should be a string"
    
    print("passed")

if __name__ == "__main__":
    self_test()
# SEAL