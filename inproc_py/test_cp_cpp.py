import cupy as cp

# 1. The CUDA Kernel
# 'raw T bytes' allows us to index into the 2D grid manually
# 'int32 width' tells the kernel how many characters are in each hex string
hex_parser = cp.ElementwiseKernel(
    'raw int32 hex_matrix, int32 width',
    'int64 out',
    '''
    long long value = 0;
    // Calculate the starting position for this specific thread
    int row_start = i * width;

    for (int j = 0; j < width; j++) {
        int c = hex_matrix[row_start + j];

        // 0 is our padding/null terminator
        if (c == 0) break;

        // Skip '0x' or '0X' if they exist in the first two positions
        if (j == 0 && c == 48) continue; // '0'
        if (j == 1 && (c == 120 || c == 88)) continue; // 'x' or 'X'

        int digit = 0;
        if (c >= 48 && c <= 57)      digit = c - 48; // 0-9
        else if (c >= 65 && c <= 70) digit = c - 55; // A-F
        else if (c >= 97 && c <= 102)digit = c - 87; // a-f
        else continue; // Ignore non-hex characters

        // Shift existing value left by 4 bits (1 hex digit) and OR the new digit
        value = (value << 4) | digit;
    }
    out = value;
    ''',
    'hex_parser')

def process_hex_matrix(matrix_list):
    # 1. Move the array of arrays to GPU
    # We ensure it's a 2D CuPy array (Matrix)
    # If your input is already a CuPy array, this is nearly instant
    gpu_matrix = cp.array(matrix_list, dtype=cp.int32)
    
    num_strings = gpu_matrix.shape[0]
    width = gpu_matrix.shape[1]
    
    # 2. Prepare the output array on the GPU
    results = cp.zeros(num_strings, dtype=cp.int64)
    
    # 3. Launch the Kernel
    # 'i' in the kernel represents the index of the output array
    hex_parser(gpu_matrix, width, results)
    
    return results

# --- Example Usage ---
# Representing "1A", "FF", "0x10" as ASCII integer arrays
# Padded with 0 to maintain a rectangular matrix
input_data = [
    [49, 65, 0, 0],   # "1A"
    [70, 70, 0, 0],   # "FF"
    [48, 120, 49, 48] # "0x10"
]

gpu_ints = process_hex_matrix(input_data)

print("Input ASCII Matrix:\n", cp.array(input_data))
print("Converted Integers on GPU:", gpu_ints)
