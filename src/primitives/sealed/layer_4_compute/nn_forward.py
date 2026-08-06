import os
import sys
import math
import random
import struct
from typing import List, Tuple

# Insert paths for crypto, consensus, and communications layers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_3_comms'))

# Relative import for other P4 modules (if any)
# from . import some_other_module

class Layer:
    """
    A base class representing a neural network layer.
    
    Attributes:
        weights (List[List[float]]): The weights of the layer.
        biases (List[float]): The biases of the layer.
    """
    def __init__(self, weights: List[List[float]], biases: List[float]):
        self.weights = weights
        self.biases = biases

    def forward(self, inputs: List[float]) -> List[float]:
        """
        Perform a forward pass through the layer.

        Args:
            inputs (List[float]): The input values to the layer.

        Returns:
            List[float]: The output values after applying the weights and biases.
        """
        outputs = []
        for i in range(len(self.biases)):
            weighted_sum = sum(w * x for w, x in zip(self.weights[i], inputs)) + self.biases[i]
            outputs.append(weighted_sum)
        return outputs

class ActivationLayer:
    """
    A class representing an activation layer.

    Attributes:
        activation_func (Callable[[float], float]): The activation function to apply.
    """
    def __init__(self, activation_func):
        self.activation_func = activation_func

    def forward(self, inputs: List[float]) -> List[float]:
        """
        Perform a forward pass through the activation layer.

        Args:
            inputs (List[float]): The input values to the activation function.

        Returns:
            List[float]: The output values after applying the activation function.
        """
        return [self.activation_func(x) for x in inputs]

def sigmoid(x: float) -> float:
    """
    A sigmoid activation function.

    Args:
        x (float): The input value.

    Returns:
        float: The output value after applying the sigmoid function.
    """
    return 1 / (1 + math.exp(-x))

class NeuralNetwork:
    """
    A class representing a simple neural network composed of layers.

    Attributes:
        layers (List[Layer or ActivationLayer]): The list of layers in the network.
    """
    def __init__(self, layers: List[Layer or ActivationLayer]):
        self.layers = layers

    def forward(self, inputs: List[float]) -> List[float]:
        """
        Perform a forward pass through the entire neural network.

        Args:
            inputs (List[float]): The input values to the network.

        Returns:
            List[float]: The output values after passing through all layers.
        """
        outputs = inputs
        for layer in self.layers:
            outputs = layer.forward(outputs)
        return outputs

def initialize_weights_and_biases(num_inputs: int, num_outputs: int) -> Tuple[List[List[float]], List[float]]:
    """
    Initialize weights and biases for a layer.

    Args:
        num_inputs (int): The number of input neurons.
        num_outputs (int): The number of output neurons.

    Returns:
        Tuple[List[List[float]], List[float]]: A tuple containing the initialized weights and biases.
    """
    weights = [[random.random() for _ in range(num_inputs)] for _ in range(num_outputs)]
    biases = [random.random() for _ in range(num_outputs)]
    return weights, biases

def self_test():
    """
    Perform a self-test to ensure the neural network forward pass works correctly.

    Prints "passed" if the test is successful.
    """
    # Initialize weights and biases
    input_size = 3
    hidden_size = 4
    output_size = 2

    # Layer 1: Input -> Hidden
    layer1_weights, layer1_biases = initialize_weights_and_biases(input_size, hidden_size)
    layer1 = Layer(layer1_weights, layer1_biases)

    # Activation function for Layer 1
    activation1 = ActivationLayer(sigmoid)

    # Layer 2: Hidden -> Output
    layer2_weights, layer2_biases = initialize_weights_and_biases(hidden_size, output_size)
    layer2 = Layer(layer2_weights, layer2_biases)

    # Activation function for Layer 2
    activation2 = ActivationLayer(sigmoid)

    # Create the neural network with the layers and activations
    nn = NeuralNetwork([layer1, activation1, layer2, activation2])

    # Test inputs
    test_input = [0.5, 0.3, 0.8]
    expected_output_length = output_size

    # Perform a forward pass
    result = nn.forward(test_input)

    # Check if the result has the correct length
    assert len(result) == expected_output_length, "Output length mismatch"

    print("passed")

if __name__ == "__main__":
    self_test()

# SEAL