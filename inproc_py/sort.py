import cupy as cp
import numpy as np

def proc_gpu_arrays(pointers, size, dtype_str, func):
    print(f"[Python] Received {len(pointers)} pointers.")

    try:
        dtype = np.dtype(dtype_str)
        itemsize = dtype.itemsize
    except TypeError:
        print(f"[Python] Error: Invalid dtype string '{dtype_str}'")
        return []

    sorted_pointers = []
    for i, ptr in enumerate(pointers):
        try:
            unowned_mem = cp.cuda.UnownedMemory(ptr, size * itemsize, None)

            memptr = cp.cuda.MemoryPointer(unowned_mem, 0)

            arr = cp.ndarray((size,), dtype=dtype, memptr=memptr)
            print(f"[Python] Wrapped pointer {i} into a CuPy array.")

            print(f'\033[35mcalling {func} with \033[33;1m{type(arr)} {arr}\033[m')
            sorted_arr = func(arr)
            print(f"[Python] Sorted array {i}.")

            sorted_ptr = sorted_arr.data.ptr
            sorted_pointers.append(sorted_ptr)

        except Exception as e:
            print(f"[Python] An error occurred while processing pointer {i}: {e}")
            return []

    print(f"[Python] Returning {len(sorted_pointers)} pointers to sorted arrays.")
    return sorted_pointers

def max_gpu_arrays(pointers, size, dtype_str):
    return proc_gpu_arrays(pointers, size, dtype_str, cp.max)
def sort_gpu_arrays(pointers, size, dtype_str):
    return proc_gpu_arrays(pointers, size, dtype_str, cp.sort)