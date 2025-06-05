import numpy as np

def normalize_array(arr):
    """
    Normalizes a NumPy array to have 0 mean and a standard deviation of 1.

    Args:
        arr: A NumPy array of floating-point numbers.

    Returns:
        A NumPy array with the same shape as arr, but with normalized values.
        Returns the original array if it has only one element or if its standard 
        deviation is zero (to avoid division by zero).
    """

    arr = np.asarray(arr)  # Ensure it's a NumPy array

    # if arr.size <= 1:  # Handle edge cases: single-element array
    #     return arr

    mean = np.mean(arr)
    std_dev = np.std(arr)

    if std_dev == 0: # Handle edge case where standard deviation is zero.
        return arr - mean
    
    normalized_arr = (arr - mean) / std_dev
    return normalized_arr

# Example usage:
data = np.array([1.0, 2.5, 3.0, 4.5, 5.0])
normalized_data = normalize_array(data)
print('full array\nOriginal data:', data, 'mean =', np.mean(data))
print('Normalized data:', normalized_data)
print('Mean of normalized data:', np.mean(normalized_data))
print('Standard deviation of normalized data:', np.std(normalized_data))

# Example with a single element array
single_element_array = np.array([5.0])
normalized_single = normalize_array(single_element_array)
print('\nsingle val array')
print('Original single element array:', single_element_array)
print('Normalized single element array:', normalized_single)

# Example with zero standard deviation
zero_std_array = np.array([5.0, 5.0, 5.0])
normalized_zero_std = normalize_array(zero_std_array)
print('\nconstant array')
print('Original zero std array:', zero_std_array)
print('Normalized zero std array:', normalized_zero_std)

empty_array = np.array([]) # testing with an empty array
normalized_empty = normalize_array(empty_array)
print('\nempty array')
print('Original empty array:', empty_array)
print('Normalized empty array:', normalized_empty)