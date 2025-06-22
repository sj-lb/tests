// g++ -g dt_test.cpp thrust_stuff.o -o cpp_side.out\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -I/home/johnny/git/sqream/rt/dev/cpp\
 -lcuda -lcudart\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib64

#include <iostream>
#include <cuda_runtime_api.h>
#include <string>
#include <vector>
#include "thrust_stuff.cuh"

// #include <basic/utils/cpp-base64/base64.h> // TODO: find non-sqream version
std::string
base64_encode(unsigned char const* bytes_to_encode, size_t in_len)
{
    constexpr const char* base64_chars = 
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "+/";
    size_t len_encoded = (in_len + 2) / 3 * 4;
    unsigned char trailing_char = '=';

    std::string ret;
    ret.reserve(len_encoded);

    unsigned int pos = 0;
    while (pos < in_len) {
        ret.push_back(base64_chars[(bytes_to_encode[pos + 0] & 0xfc) >> 2]);

        if (pos + 1 < in_len) {
            ret.push_back(base64_chars
                              [((bytes_to_encode[pos + 0] & 0x03) << 4) +
                               ((bytes_to_encode[pos + 1] & 0xf0) >> 4)]);

            if (pos + 2 < in_len) {
                ret.push_back(base64_chars
                                  [((bytes_to_encode[pos + 1] & 0x0f) << 2) +
                                   ((bytes_to_encode[pos + 2] & 0xc0) >> 6)]);
                ret.push_back(base64_chars[bytes_to_encode[pos + 2] & 0x3f]);
            }
            else {
                ret.push_back(
                    base64_chars[(bytes_to_encode[pos + 1] & 0x0f) << 2]);
                ret.push_back(trailing_char);
            }
        }
        else {
            ret.push_back(
                base64_chars[(bytes_to_encode[pos + 0] & 0x03) << 4]);
            ret.push_back(trailing_char);
            ret.push_back(trailing_char);
        }

        pos += 3;
    }


    return ret;
}



int main() {
    constexpr size_t num_dts = 3;
    constexpr size_t total_bytes = num_dts * 8;
    void* p;
    if (cudaSuccess != cudaMalloc(&p, total_bytes))
        std::cerr << "allocating " << total_bytes << " bytes on gpu failed\n";
    unsigned char hdl_buf[sizeof(cudaIpcMemHandle_t)] = "";
    if (cudaSuccess != cudaIpcGetMemHandle(
            reinterpret_cast<cudaIpcMemHandle_t*>(hdl_buf),
            p))
        std::cerr << "gpu handle acquisition failed";
    std::string hdl_str =
        base64_encode(hdl_buf, sizeof(cudaIpcMemHandle_t));
    std::cout << "\033[35mcuda ipc handle(base64 encoded): \033[33m"
              << hdl_str << "\033[35m\nwaiting for python... \033[m";
    std::string nothing;
    std::cin >> nothing;
    size_t iter[num_dts] = {0};
    cudaError_t status = cudaMemcpy(
        iter,
        p,
        num_dts * sizeof(size_t),
        cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d code %d (%s) : %s\n",
                __FILE__, __LINE__, (int)status, cudaGetErrorName(status), cudaGetErrorString(status));
    }
    for (size_t i = 0; i < num_dts; ++i)
        std::cout << iter[i] << std::endl;
    
    void* p2;
    if (cudaSuccess != cudaMalloc(&p2, total_bytes))
        std::cerr << "allocating " << total_bytes << " bytes on gpu failed\n";
    thrust_sqfy_dt((int64_t*)p2, (const int64_t*)p, num_dts);

    status = cudaMemcpy(
        iter,
        p2,
        num_dts * sizeof(size_t),
        cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) {
        fprintf(stderr, "CUDA error at %s:%d code %d (%s) : %s\n",
                __FILE__, __LINE__, (int)status, cudaGetErrorName(status), cudaGetErrorString(status));
    }
    for (size_t i = 0; i < num_dts; ++i)
        std::cout << iter[i] << std::endl;
    
    cudaFree(p);
    cudaFree(p2);
    return 0;
}