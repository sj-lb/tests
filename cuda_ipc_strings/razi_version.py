import cudf
import numpy as np
from numba import cuda
from cudf.core.buffer import Buffer

def create_cudf_series_from_ipc(strings_pointer, offsets_pointer, lengths_pointer, num_strings):
    """
    Create a cudf.Series from IPC-shared CUDA pointers.

    Parameters:
    - strings_pointer: Device pointer to the characters buffer.
    - offsets_pointer: Device pointer to the offsets buffer.
    - lengths_pointer: Host pointer to the lengths of each string.
    - num_strings: Number of strings in the series.

    Returns:
    - cudf.Series: The reconstructed Series.
    """
    # Convert pointers to CUDA device arrays
    strings_dev_arr = cuda.device_array_from_ptr(strings_pointer, lengths_pointer.sum(), dtype=np.uint8)
    offsets_dev_arr = cuda.device_array_from_ptr(offsets_pointer, num_strings + 1, dtype=np.int32)
   
    # Create buffers for cudf.Series
    chars_buffer = Buffer(strings_dev_arr)
    offsets_buffer = Buffer(offsets_dev_arr)

    # Create cudf Series from these buffers
    series = cudf.Series._from_data(
        {
            "data": chars_buffer,
            "offsets": offsets_buffer,
        },
        index=cudf.RangeIndex(num_strings),
    )

    return series

# Example usage
if __name__ == "__main__":
    # Input Series to mimic IPC behavior
    original_series = cudf.Series(["a", "bcd", "efgh"])
   
    # Extract raw buffers from the Series
    data_buffer = original_series._column.data_array_view
    offsets_buffer = original_series._column.offsets
    string_lengths = np.array([len(s) for s in original_series.to_pandas()], dtype=np.int32)
   
    # Simulate sending pointers via IPC
    strings_pointer = data_buffer.device_ctypes_pointer.value
    offsets_pointer = offsets_buffer.device_ctypes_pointer.value
   
    # Recreate cudf.Series from IPC pointers
    recreated_series = create_cudf_series_from_ipc(
        strings_pointer, offsets_pointer, string_lengths, len(original_series)
    )
   
    print("Original Series:")
    print(original_series)
    print("\nRecreated Series:")
    print(recreated_series)