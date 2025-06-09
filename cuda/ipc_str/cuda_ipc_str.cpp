// g++ -g cuda_ipc_str.cpp -o cpp_side.out\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -I/home/sqream/git/sqream/dev/cpp\
 -lcuda -lcudart\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib64

#include <iostream>
#include <cuda_runtime_api.h>
#include <string>
#include <vector>
#include <numeric>

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

size_t align_size(size_t size) {
    return size % 8 ? size + 8 - (size % 8) : size;
}

int main() {
    std::vector<std::string> strings = {
        "there is a house in new orleans",
        "they call the rising sun",
        "and it's been the ruin of many a poor boy",
        "and god I know I'm one"};
    
    std::vector<size_t> lens;
    for (std::string s : strings)
        lens.push_back(s.length());
    
    size_t num_rows = lens.size();
    size_t total_bytes = num_rows * sizeof(size_t) + std::accumulate(
        strings.begin(),
        strings.end(),
        0lu,
        [](size_t l, std::string s) -> size_t {
            return l + align_size(s.length());});
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
              << hdl_str << "\033[m\n";
    char* iter = reinterpret_cast<char*>(p);
    if (cudaSuccess != cudaMemcpy(
            iter,
            lens.data(),
            num_rows * sizeof(size_t),
            cudaMemcpyHostToDevice))
        std::cerr << "copying lens to gpu failed\n";
    iter += num_rows * sizeof(size_t);
    for (std::string s : strings) {
        if (cudaSuccess != cudaMemcpy(
                iter,
                s.c_str(),
                s.length(),
                cudaMemcpyHostToDevice))
            std::cerr << "copying \"" << s << "\" to gpu failed\n";
        iter += align_size(s.length());
    }

    cudaFree(p);
    return 0;
}