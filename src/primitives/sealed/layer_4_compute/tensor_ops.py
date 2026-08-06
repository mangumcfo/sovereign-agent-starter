import sys
import os
import math
import random
from typing import List, Tuple

# Import rules for the sovereign compute layer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_1_root'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_2_trunk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layer_3_comms'))

# Pure Python tensor operations for neural network inference

def matrix_multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """
    Perform matrix multiplication of two matrices A and B.

    Parameters:
    A (List[List[float]]): The first matrix.
    B (List[List[float]]): The second matrix.

    Returns:
    List[List[float]]: The result of the matrix multiplication.

    Raises:
    ValueError: If the number of columns in A does not match the number of rows in B.
    """
    if len(A[0]) != len(B):
        raise ValueError("Number of columns in A must be equal to the number of rows in B")

    result = [[sum(a * b for a, b in zip(A_row, B_col)) for B_col in zip(*B)] for A_row in A]
    return result

def convolve2d(input_matrix: List[List[float]], kernel: List[List[float]]) -> List[List[float]]:
    """
    Perform 2D convolution on an input matrix using a given kernel.

    Parameters:
    input_matrix (List[List[float]]): The input matrix.
    kernel (List[List[float]]): The convolution kernel.

    Returns:
    List[List[float]]: The result of the 2D convolution.
    """
    k_height = len(kernel)
    k_width = len(kernel[0])
    i_height = len(input_matrix)
    i_width = len(input_matrix[0])

    output_height = i_height - k_height + 1
    output_width = i_width - k_width + 1

    result = [[0 for _ in range(output_width)] for _ in range(output_height)]

    for y in range(output_height):
        for x in range(output_width):
            sub_matrix = [row[x:x+k_width] for row in input_matrix[y:y+k_height]]
            conv_value = sum(a * b for a, b in zip([item for sublist in sub_matrix for item in sublist],
                                                  [item for sublist in kernel for item in sublist]))
            result[y][x] = conv_value

    return result

def max_pooling(input_matrix: List[List[float]], pool_size: Tuple[int, int]) -> List[List[float]]:
    """
    Perform 2D max pooling on an input matrix.

    Parameters:
    input_matrix (List[List[float]]): The input matrix.
    pool_size (Tuple[int, int]): The size of the pooling window.

    Returns:
    List[List[float]]: The result of the 2D max pooling.
    """
    p_height, p_width = pool_size
    i_height = len(input_matrix)
    i_width = len(input_matrix[0])

    output_height = i_height // p_height
    output_width = i_width // p_width

    result = [[0 for _ in range(output_width)] for _ in range(output_height)]

    for y in range(output_height):
        for x in range(output_width):
            sub_matrix = [row[x*p_width:(x+1)*p_width] for row in input_matrix[y*p_height:(y+1)*p_height]]
            max_value = max(max(row) for row in sub_matrix)
            result[y][x] = max_value

    return result

def relu(input_matrix: List[List[float]]) -> List[List[float]]:
    """
    Apply the ReLU activation function element-wise to an input matrix.

    Parameters:
    input_matrix (List[List[float]]): The input matrix.

    Returns:
    List[List[float]]: The result of applying ReLU to each element.
    """
    return [[max(0, value) for value in row] for row in input_matrix]

def sigmoid(input_matrix: List[List[float]]) -> List[List[float]]:
    """
    Apply the Sigmoid activation function element-wise to an input matrix.

    Parameters:
    input_matrix (List[List[float]]): The input matrix.

    Returns:
    List[List[float]]: The result of applying Sigmoid to each element.
    """
    return [[1 / (1 + math.exp(-value)) for value in row] for row in input_matrix]

if __name__ == "__main__":
    # Self-test
    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]
    assert matrix_multiply(A, B) == [[19, 22], [43, 50]]

    input_matrix = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12]
    ]
    kernel = [
        [1, 0],
        [0, 1]
    ]
    assert convolve2d(input_matrix, kernel) == [
        [7, 9, 11],
        [15, 17, 19]
    ]

    input_matrix_pooling = [
        [1, 3, 2, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16]
    ]
    assert max_pooling(input_matrix_pooling, (2, 2)) == [
        [6, 8],
        [14, 16]
    ]

    input_matrix_relu = [[-1, 0, 2], [-3, 4, -5]]
    assert relu(input_matrix_relu) == [[0, 0, 2], [0, 4, 0]]

    input_matrix_sigmoid = [[0, -1, 1]]
    expected_sigmoid_output = [[0.5, 1 / (1 + math.exp(1)), 1 / (1 + math.exp(-1))]]
    assert all(abs(a - b) < 1e-6 for a, b in zip(sigmoid(input_matrix_sigmoid)[0], expected_sigmoid_output[0]))

    print("passed")

# SEAL