import os
import sys
import hashlib
import base64
import bisect

# Importing from layer_1_root for cryptographic functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from keygen import generate_keypair, KeyPair
from sign import sign
from verify import verify

# Placeholder for consensus imports from layer_2_trunk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))

# Constants
K = 8  # Number of nodes in a k-bucket
ID_SIZE_BITS = 160  # Size of the node ID in bits (commonly SHA-1 size)
MAX_NODES = 2 ** ID_SIZE_BITS

class Node:
    """
    Represents a node in the Kademlia DHT.
    """

    def __init__(self, node_id: bytes):
        self.node_id = node_id
        self.address = None  # Placeholder for actual address (IP, port)

    def distance(self, other_node_id: bytes) -> int:
        """
        Calculate the XOR distance between this node and another node.
        :param other_node_id: The ID of the other node.
        :return: The XOR distance as an integer.
        """
        return int.from_bytes(self.node_id, 'big') ^ int.from_bytes(other_node_id, 'big')

class KBucket:
    """
    Represents a k-bucket in the Kademlia DHT.
    """

    def __init__(self):
        self.nodes = []

    def add_node(self, node: Node) -> bool:
        """
        Add a node to the k-bucket. If the bucket is full, return False.
        :param node: The node to be added.
        :return: True if the node was added, False otherwise.
        """
        if len(self.nodes) < K:
            bisect.insort(self.nodes, node, key=lambda n: n.node_id)
            return True
        else:
            return False

    def remove_node(self, node_id: bytes):
        """
        Remove a node from the k-bucket by its ID.
        :param node_id: The ID of the node to be removed.
        """
        self.nodes = [node for node in self.nodes if node.node_id != node_id]

    def get_closest_nodes(self, target_id: bytes, num_nodes=K) -> list:
        """
        Get the closest nodes to a given target ID.
        :param target_id: The target node ID.
        :param num_nodes: The number of closest nodes to retrieve.
        :return: A list of the closest nodes.
        """
        return sorted(self.nodes, key=lambda n: n.distance(target_id))[:num_nodes]

class KademliaDHT:
    """
    Represents a Kademlia Distributed Hash Table (DHT).
    """

    def __init__(self, node_id: bytes):
        self.node = Node(node_id)
        self.routing_table = [KBucket() for _ in range(ID_SIZE_BITS)]
        self.storage = {}

    def add_node(self, node: Node) -> bool:
        """
        Add a node to the appropriate k-bucket in the routing table.
        :param node: The node to be added.
        :return: True if the node was added, False otherwise.
        """
        distance = self.node.distance(node.node_id)
        bucket_index = min(ID_SIZE_BITS - 1, distance.bit_length())
        return self.routing_table[bucket_index].add_node(node)

    def remove_node(self, node_id: bytes):
        """
        Remove a node from the routing table by its ID.
        :param node_id: The ID of the node to be removed.
        """
        distance = self.node.distance(node_id)
        bucket_index = min(ID_SIZE_BITS - 1, distance.bit_length())
        self.routing_table[bucket_index].remove_node(node_id)

    def find_closest_nodes(self, target_id: bytes) -> list:
        """
        Find the closest nodes to a given target ID.
        :param target_id: The target node ID.
        :return: A list of the closest nodes.
        """
        bucket_index = min(ID_SIZE_BITS - 1, self.node.distance(target_id).bit_length())
        closest_nodes = []
        for i in range(ID_SIZE_BITS):
            index = (bucket_index + i) % ID_SIZE_BITS
            closest_nodes.extend(self.routing_table[index].get_closest_nodes(target_id))
        return sorted(closest_nodes, key=lambda n: n.distance(target_id))[:K]

    def store_value(self, key: bytes, value: bytes):
        """
        Store a value in the DHT.
        :param key: The key for the value.
        :param value: The value to be stored.
        """
        self.storage[key] = value

    def retrieve_value(self, key: bytes) -> bytes:
        """
        Retrieve a value from the DHT by its key.
        :param key: The key of the value to be retrieved.
        :return: The value if found, None otherwise.
        """
        return self.storage.get(key)

def generate_node_id():
    """
    Generate a random node ID using SHA-1 hash.
    :return: A random node ID as bytes.
    """
    return hashlib.sha1(os.urandom(20)).digest()

def test_kademlia_dht():
    # Create nodes
    node_ids = [generate_node_id() for _ in range(2 * K)]
    dhts = [KademliaDHT(node_id) for node_id in node_ids]

    # Bootstrap the network by adding nodes to each other's routing tables
    for i, dht in enumerate(dhts):
        for j in range(len(dhts)):
            if i != j:
                dht.add_node(Node(dhts[j].node.node_id))

    # Test finding closest nodes
    target_id = generate_node_id()
    closest_nodes = dhts[0].find_closest_nodes(target_id)
    assert len(closest_nodes) <= K

    # Test storing and retrieving values
    key = b'test_key'
    value = b'test_value'
    dhts[0].store_value(key, value)
    retrieved_value = dhts[0].retrieve_value(key)
    assert retrieved_value == value

    print("passed")

if __name__ == "__main__":
    test_kademlia_dht()
# SEAL