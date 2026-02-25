import numpy as np
import cupy as cp
from numba import cuda

@cp.vectorize
def simple_hex_convert(h_val):
    return int(h_val)

def run_vectorized_hex(hex_list):
    gpu_bytes = cp.array(hex_list)
    byte_grid = gpu_bytes.view(cp.uint8).reshape(len(hex_list), -1)
    results = simple_hex_convert(byte_grid)
    return results

cuda_source = r'''
extern "C" __global__
void hex_to_int_kernel(const unsigned char* bytes, long long* results, int n, int width) {
    int tid = blockDim.x * blockIdx.x + threadIdx.x;
    if (tid >= n) return;
    long long val = 0;
    int start = 0;
    // Check for 0x or 0X prefix at the start of the row
    if (bytes[tid * width] == 48) { // '0'
        unsigned char next = bytes[tid * width + 1];
        if (next == 120 || next == 88) { // 'x' or 'X'
            start = 2;
        }
    }
    // Bit-shifting loop: processes characters as raw ASCII bytes
    for (int i = start; i < width; i++) {
        unsigned char c = bytes[tid * width + i];
        // Break on null terminator (padding)
        if (c == 0) break;
        int digit;
        if (c >= '0' && c <= '9')      digit = c - '0';
        else if (c >= 'a' && c <= 'f') digit = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') digit = c - 'A' + 10;
        else break; // Invalid character
        val = (val << 4) | (digit & 0xF);
    }
    results[tid] = val;
}
'''
# 2. Compile kernel once (cached for future use)
hex_kernel = cp.RawKernel(cuda_source, 'hex_to_int_kernel')
def fast_gpu_convert(hex_list):
    n = len(hex_list)
    # Vectorized conversion of Python strings to fixed-width GPU bytes
    gpu_strings = cp.array(hex_list, dtype='S')
    width = gpu_strings.dtype.itemsize
    # Re-interpret as raw byte grid (zero-copy)
    d_bytes = gpu_strings.view(cp.uint8)
    d_results = cp.zeros(n, dtype=cp.int64)
    # 3. Launch Kernel: Grid and Block configuration
    threads_per_block = 256
    blocks_per_grid = (n + threads_per_block - 1) // threads_per_block
    hex_kernel((blocks_per_grid,), (threads_per_block,),
               (d_bytes, d_results, n, width))
    return d_results

# CUDA Kernel: Each thread processes one string
@cuda.jit
def hex_to_int_jit(byte_array, results):
    # Get the index of the current thread
    idx = cuda.grid(1)

    if idx < byte_array.shape[0]:
        val = 0
        for i in range(byte_array.shape[1]):
            char = byte_array[idx, i]

            # End of string (null terminator or padding)
            if char == 0:
                break

            # Skip '0' and 'x' or 'X' prefixes
            if char == 48 or char == 120 or char == 88: # '0', 'x', 'X'
                if i < 2: # Only skip if it's at the start
                    continue

            # Convert ASCII to numerical value
            if 48 <= char <= 57:   # 0-9
                digit = char - 48
            elif 65 <= char <= 70: # A-F
                digit = char - 55
            elif 97 <= char <= 102: # a-f
                digit = char - 87
            else:
                val = -1
                break # Invalid character

            val = (val << 4) | digit # Shift left 4 bits and add new digit

        results[idx] = val

def run_gpu_conversion(hex_list):
    max_len = max(len(s) for s in hex_list)
    np_bytes = np.zeros((len(hex_list), max_len), dtype=np.uint8)
    for i, s in enumerate(hex_list):
        # Remove '0x' if present for cleaner parsing, or keep it and let kernel skip
        b_str = s.encode('utf-8')
        np_bytes[i, :len(b_str)] = list(b_str)

    # 2. Allocate memory on GPU
    d_bytes = cuda.to_device(np_bytes)
    d_results = cuda.device_array(len(hex_list), dtype=np.int64)

    # 3. Configure GPU Threads and Blocks
    threads_per_block = 256
    blocks_per_grid = (len(hex_list) + (threads_per_block - 1)) // threads_per_block

    # 4. Launch Kernel
    hex_to_int_jit[blocks_per_grid, threads_per_block](d_bytes, d_results)

    # 5. Bring result back to CuPy or NumPy
    final_results = cp.asarray(d_results)
    return final_results


# --- Execution ---
if __name__ == "__main__":
    hex_data = ["0x1A", "0xFF", "0xABC", "10", "deadbeef", "123rglek"]
    gpu_ints = run_gpu_conversion(hex_data)

    print(f"Hex strings: {hex_data}")
    print(f"GPU Integers: {gpu_ints}")
    
    # hex_data = ["0x1A", "0xFF", "deadbeef", "123", "0xabc123"]
    # results = fast_gpu_convert(hex_data)
    # for s, r in zip(hex_data, results.tolist()):
    #     print(f"{s} -> {r}")
    
    # hex_data = ["10", "0x20", "123", "40"] # Simple numeric strings for demo
    # gpu_ints = run_vectorized_hex(hex_data)
    # print(f"Hex strings: {hex_data}")
    # print(f"GPU Results:\n{gpu_ints}")