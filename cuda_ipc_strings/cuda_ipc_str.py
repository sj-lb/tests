import sys

import base64
import numpy as np
import ctypes
import inspect
import time

from cuda import cudart
import cupy as cp
import cudf
import pycuda.driver as drv
import rmm

def align_size(size):
    if not size % 8:
        return size
    return size + (8 - size % 8)

def get_gpu_ptr(hdl_str):
    hdl = cudart.cudaIpcMemHandle_t()
    hdl.reserved = base64.b64decode(hdl_str)
    err, gpu_ptr = cudart.cudaIpcOpenMemHandle(
        hdl, cudart.cudaIpcMemLazyEnablePeerAccess)
    if err != cudart.cudaError_t.cudaSuccess:
        raise RuntimeError(f'Failed to open IPC handle: {err}')
    return gpu_ptr

def gpu_mem_to_series(gpu_base, offset, dtype, shape):
    if dtype == np.object_:
        return None
    return cudf.Series(cp.ndarray(
        shape=shape,
        dtype=dtype,
        memptr=cp.cuda.MemoryPointer(cp.cuda.UnownedMemory(
                gpu_base,
                np.prod(shape) * np.dtype(dtype).itemsize,
                None),
            offset)))

def align_strings(dataframe, column):
    strings = dataframe[column].values  
    aligned_bytes = bytearray()  
    
    for s in strings:
        encoded = s.encode("utf-8") 
        length = len(encoded)  
        padding = (8 - (length % 8)) % 8  
        aligned_bytes.extend(encoded + b'\x00' * padding)  
    
    return aligned_bytes

        
if __name__ == '__main__':
    try:
        gpu_base = get_gpu_ptr(sys.argv[1])
    except RuntimeError as e:
        print(e)

    series_list = [gpu_mem_to_series(
            gpu_base,
            request.gpu_offsets[i],
            types[i],
            (request.rows,))
        for i in range(len(request.gpu_offsets))]
    
    for i in range(len(request.types)):
        if request.types[i] == sqream_string:
            validate_types(types, i)
        
        strings = [func(
            j,
            series_list[i - 1][j],
            cp.cuda.MemoryPointer(cp.cuda.UnownedMemory(
                        gpu_base,
                        len_col[j],
                        None))) for j in range(request.rows)]
    # np_list = []
    offset = 0
    i = 0
    while i < len(request.offsets):
        if (i  + 1) < len(request.offsets) and types[i + 1] == np.object_:  # Handling string type
            # Read sizes array (from next type)
            size_type = types[i]

            mapfile.seek(offset)
            sizes = np.frombuffer(
                mapfile.read(request.offsets[i]),
                dtype=size_type
            )
            offset += request.offsets[i]
            
            i += 1  
            # Read the strings based on the sizes
            strings = []
            for size in sizes:  # Sizes represent the total chunk sizes
                bytes_read = 0
                decoded_string = ""
                while bytes_read < size:
                    mapfile.seek(offset)
                    
                    # Read one aligned chunk
                    aligned_size = 8  # Strings are aligned to 8-byte boundaries
                    raw_data = mapfile.read(aligned_size)
                    bytes_read += aligned_size
                    offset += aligned_size

                    # Decode and clean the string
                    decoded_string += raw_data.decode('utf-8').rstrip('\x00')  # Remove padding
                # Only append non-empty strings
                if decoded_string:
                    strings.append(decoded_string)
            

            np_list.append(strings)
        else:
            mapfile.seek(offset)
            np_list.append(np.frombuffer(
                mapfile.read(request.offsets[i]),
                dtype=types[i]))
            offset = offset + request.offsets[i]
        i += 1
    

    result = getattr(module, request.func_name)(pd.DataFrame(
            {i: series for i, series in enumerate(np_list[:])}))
    
    out_rows = 0
    try:

        out_rows = result.shape[0]

        if request.rows != out_rows:
            raise ValueError(f"Mismatch: request.rows ({request.rows}) != out_rows ({out_rows})")
        first_column = result.columns[0]

        if type_map[request.ret_type] != result[first_column].dtype:
            raise ValueError(f"Mismatch: request.type ({type_map[request.ret_type]}) != dtype ({result[first_column].dtype})")
        
        dtype_itemsize = result[first_column].dtype.itemsize
        
        if request.ret_type == ftblob:
            sizes_before_alignment = [len(s.encode("utf-8")) for s in result[first_column]]
            print(sizes_before_alignment)
            sizes_array = np.array(sizes_before_alignment, dtype=np.int32)
            sizes_as_bytes = sizes_array.tobytes()
            print(sizes_array)
            print(len(sizes_as_bytes))
            array = align_strings(result,first_column)
            print(array)
            mem_size = len(array) + len(sizes_as_bytes)
            print(mem_size)
            resize_shared_memory(shm_name, mem_size)
            print("resized")
            mapfile[:len(sizes_as_bytes)] = sizes_as_bytes
            mapfile[len(sizes_as_bytes):len(sizes_as_bytes) + len(array)] = array
        else:
            mem_size = (out_rows * dtype_itemsize)
            mapfile[:(out_rows * dtype_itemsize)] = result.to_numpy().tobytes()
    except Exception as e:
        print(f"Exception occurred: {e}")
        out_rows = -1
        mem_size = -1
        pass
    mapfile.close()
    shm.close_fd()
    del shm
    del mapfile
    return py_udf_pb2.UdfStatus(status=mem_size)
