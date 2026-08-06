import os
import sys
import hashlib
import base64
from collections import deque, defaultdict

# Import rules for crypto and consensus layers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from keygen import generate_keypair, KeyPair
from sign import sign
from verify import verify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))

class Node:
    """
    A node in the DAG structure representing a piece of content.
    
    Attributes:
        id (str): Unique identifier for the node.
        data (bytes): The content/data stored at this node.
        parent_ids (list): List of IDs of parent nodes.
        signature (bytes): Signature of the node's data and parent IDs.
        keypair (KeyPair): Key pair used to sign the node.
    """
    
    def __init__(self, data: bytes, parent_ids: list = None):
        self.data = data
        self.parent_ids = parent_ids if parent_ids is not None else []
        self.keypair = generate_keypair()
        self.id = self._compute_id()
        self.signature = sign(self.keypair.private_key, f"{self.id}{self.parent_ids}".encode())
    
    def _compute_id(self) -> str:
        """Compute a unique identifier for the node based on its data and parent IDs."""
        hash_input = hashlib.sha256(f"{self.data}{self.parent_ids}".encode()).digest()
        return base64.b32encode(hash_input).decode().strip('=')

    def verify_node(self) -> bool:
        """Verify the integrity of the node's signature."""
        return verify(self.keypair.public_key, f"{self.id}{self.parent_ids}".encode(), self.signature)


class DAG:
    """
    Directed Acyclic Graph (DAG) for content addressing and traversal.
    
    Attributes:
        nodes (dict): Dictionary mapping node IDs to Node objects.
        adjacency_list (defaultdict): Adjacency list representation of the graph.
    """
    
    def __init__(self):
        self.nodes = {}
        self.adjacency_list = defaultdict(list)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the DAG."""
        if node.id in self.nodes:
            raise ValueError(f"Node with ID {node.id} already exists.")
        
        # Add the node
        self.nodes[node.id] = node
        
        # Update adjacency list for each parent
        for parent_id in node.parent_ids:
            if parent_id not in self.nodes:
                raise ValueError(f"Parent node with ID {parent_id} does not exist.")
            self.adjacency_list[parent_id].append(node.id)
    
    def topological_sort(self) -> list:
        """Perform a topological sort of the DAG."""
        visited = set()
        stack = []

        def dfs(v):
            visited.add(v)
            for neighbor in self.adjacency_list[v]:
                if neighbor not in visited:
                    dfs(neighbor)
            stack.append(v)

        # Perform DFS from all unvisited nodes
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)

        return stack[::-1]
    
    def traverse(self, start_node_id: str) -> list:
        """Traverse the DAG starting from a given node."""
        if start_node_id not in self.nodes:
            raise ValueError(f"Node with ID {start_node_id} does not exist.")
        
        visited = set()
        result = []

        def dfs_traversal(v):
            visited.add(v)
            result.append(v)
            for neighbor in self.adjacency_list[v]:
                if neighbor not in visited:
                    dfs_traversal(neighbor)

        dfs_traversal(start_node_id)
        return result


def self_test():
    """
    Perform a self-test of the DAG structure.
    
    Prints "passed" on success, raises an AssertionError otherwise.
    """
    # Create some nodes
    node1 = Node(data=b'Hello')
    node2 = Node(data=b'World', parent_ids=[node1.id])
    node3 = Node(data=b'!', parent_ids=[node2.id])

    # Add nodes to DAG
    dag = DAG()
    for node in [node1, node2, node3]:
        dag.add_node(node)

    # Verify nodes
    assert all(node.verify_node() for node in dag.nodes.values()), "Node verification failed."

    # Topological sort
    sorted_nodes = dag.topological_sort()
    assert len(sorted_nodes) == 3 and sorted_nodes[0] == node1.id and sorted_nodes[-1] == node3.id, \
        "Topological sort failed."

    # Node traversal
    traversed_nodes = dag.traverse(node1.id)
    assert len(traversed_nodes) == 3 and traversed_nodes[0] == node1.id and traversed_nodes[-1] == node3.id, \
        "Node traversal failed."

    print("passed")


if __name__ == "__main__":
    self_test()

# SEAL