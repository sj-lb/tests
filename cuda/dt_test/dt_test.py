import sys

import base64
import numpy as np
import ctypes
import inspect
import time

from cuda import cudart
import cupy as cp
import cudf

def get_gpu_ptr(hdl_str):
    hdl = cudart.cudaIpcMemHandle_t()
    hdl.reserved = base64.b64decode(hdl_str)
    err, gpu_ptr = cudart.cudaIpcOpenMemHandle(
        hdl, cudart.cudaIpcMemLazyEnablePeerAccess)
    if err != cudart.cudaError_t.cudaSuccess:
        raise RuntimeError(f'Failed to open IPC handle: {err}')
    return gpu_ptr

if __name__ == '__main__':
    try:
        gpu_base = get_gpu_ptr(sys.argv[1])
    except RuntimeError as e:
        print(e)
    df = cudf.Series(['2023-01-01T00:00:00.123456789', '2024-01-01T00:00:00.123456789', '2025-01-01T00:00:00.123456789'], dtype='datetime64[ns]')
    # df = cudf.Series(['2023-01-01T00:00:00.123', '2024-01-01T00:00:00.123', '2025-01-01T00:00:00.123'], dtype='datetime64[ms]')
    df = df.astype(np.int64)
    print(df)
    cp.cuda.runtime.memcpy(
        gpu_base,
        df.data.get_ptr(mode='read'),
        24,
        cp.cuda.runtime.memcpyDeviceToDevice)