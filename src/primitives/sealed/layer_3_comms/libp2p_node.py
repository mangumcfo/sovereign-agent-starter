import os
import sys
import hashlib
import base64
import random
from collections import defaultdict

# Import rules for crypto from layer_1_root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
from keygen import generate_keypair, KeyPair
from sign import sign
from verify import verify

# Import rules for consensus from layer_2_trunk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))

class MultiAddr:
    """
    A class to handle Multiaddr representation and parsing.
    
    Multiaddr is a self-describing address used in P2P networking.
    It consists of a protocol identifier and an address.
    """
    def __init__(self, addr_str):
        self.addr_str = addr_str
        self.protocols = []
        self.parse()

    def parse(self):
        """Parse the Multiaddr string into protocols and addresses."""
        parts = self.addr_str.split('/')
        if parts[0] != '':
            raise ValueError("Invalid Multiaddr format")
        for i in range(1, len(parts), 2):
            proto = parts[i]
            addr = parts[i + 1] if i + 1 < len(parts) else ''
            self.protocols.append((proto, addr))

    def __str__(self):
        return self.addr_str

class PubSub:
    """
    A class to handle publish-subscribe functionality for topics.
    
    This class manages subscriptions and distributes messages to subscribers.
    """
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, topic, callback):
        """Subscribe to a topic with a callback function."""
        if callable(callback):
            self.subscribers[topic].append(callback)
        else:
            raise ValueError("Callback must be callable")

    def unsubscribe(self, topic, callback):
        """Unsubscribe from a topic by removing the callback."""
        if callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)

    def publish(self, topic, message):
        """Publish a message to all subscribers of a topic."""
        for callback in self.subscribers[topic]:
            callback(message)

class Libp2pNode:
    """
    A class representing a node in the libp2p decentralized communication layer.
    
    This node manages peer identity, multiaddr handling, pub/sub topics, and message routing.
    """
    def __init__(self, multiaddr_str):
        self.keypair = generate_keypair()
        self.multiaddr = MultiAddr(multiaddr_str)
        self.pubsub = PubSub()
        self.peers = set()

    @property
    def peer_id(self):
        """Generate a peer ID based on the public key."""
        return base58.b58encode(hashlib.sha256(self.keypair.public_key).digest()).decode('utf-8')

    def add_peer(self, multiaddr_str):
        """Add a new peer to the node's known peers."""
        multiaddr = MultiAddr(multiaddr_str)
        self.peers.add(str(multiaddr))

    def remove_peer(self, multiaddr_str):
        """Remove a peer from the node's known peers."""
        multiaddr = MultiAddr(multiaddr_str)
        self.peers.discard(str(multiaddr))

    def subscribe(self, topic, callback):
        """Subscribe to a pub/sub topic with a callback function."""
        self.pubsub.subscribe(topic, callback)

    def unsubscribe(self, topic, callback):
        """Unsubscribe from a pub/sub topic by removing the callback."""
        self.pubsub.unsubscribe(topic, callback)

    def publish(self, topic, message):
        """Publish a message to all subscribers of a topic."""
        signed_message = self.sign_message(message)
        self.pubsub.publish(topic, signed_message)

    def sign_message(self, message):
        """Sign a message with the node's private key."""
        return sign(self.keypair.private_key, message.encode('utf-8'))

    def verify_message(self, message, signature, public_key):
        """Verify a message using its signature and public key."""
        return verify(public_key, message.encode('utf-8'), signature)

    def route_message(self, message, destination_multiaddr_str):
        """
        Route a message to the specified destination Multiaddr.
        
        In this implementation, we simulate routing by printing the message
        and the destination multiaddr. In a real-world scenario, this would involve
        actual network communication.
        """
        print(f"Routing message to {destination_multiaddr_str}: {message}")

if __name__ == "__main__":
    # Self-test: Create a node, subscribe to a topic, publish a message, and verify it
    node = Libp2pNode("/ip4/192.168.0.1/tcp/8080")
    
    def test_callback(message):
        print(f"Received message: {message}")
    
    node.subscribe("test_topic", test_callback)
    node.publish("test_topic", "Hello, libp2p!")
    
    # Verify the message
    signed_message = node.sign_message("Hello, libp2p!")
    is_valid = node.verify_message("Hello, libp2p!", signed_message, node.keypair.public_key)
    
    if is_valid:
        print("passed")
    else:
        print("failed")

# SEAL