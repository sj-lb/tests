// g++ -g olsFit_test.cpp -o test.out\
 -fconcepts -fmessage-length=0 -fPIC -fsigned-char -fstack-protector-all\
 -DUSE_TENSORPIPE -DFMT_HEADER_ONLY=1 -DSPDLOG_FMT_EXTERNAL -DUSE_C10D_GLOO\
 -DLIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -DUSE_DISTRIBUTED -DUSE_RPC\
 -isystem /usr/local/sqream-prerequisites/versions/5.22/include\
 -ldl -lrt -lcuda -lcudart -lnvToolsExt -ltreelite -lraft -lcumlprims_mg -lcuml++\
 -L/usr/local/sqream-prerequisites/versions/5.22/lib\
 -L/usr/local/sqream-prerequisites/versions/5.22/lib64

#include <rmm/device_uvector.hpp>
#include <cuml/linear_model/glm.hpp>
#include <iostream>

std::string
log_weights(const rmm::device_uvector<float>& coefs, const cudaStream_t& stream)
{
    std::string ret("[");
    for (size_t i = 0; i < coefs.size(); ++i)
        ret += std::to_string(coefs.element(i, stream)) +
               (i == coefs.size() - 1 ? "]" : ", ");
    return ret;
}

int main() {
    constexpr size_t chunk_rows = 1'000'000;
    constexpr size_t num_chunks = 4;
    constexpr size_t num_features = 1;

    rmm::mr::cuda_memory_resource upstream_mr;
    rmm::mr::pool_memory_resource pool_mr(&upstream_mr, 1lu << 30, 1lu << 32);
    // Initial pool size: 1GB, max pool size: 4GB
    rmm::mr::set_current_device_resource(&pool_mr);
    raft::handle_t raft_hdl;

    size_t total_rows = 0;

    rmm::device_uvector<float> out_coefs(
        num_features + 1,
        raft_hdl.get_stream());
    for (size_t i = 0; i < num_chunks; ++i) {
        float host_buf[chunk_rows];
        for (size_t j = 0; j < chunk_rows; ++j)
            host_buf[j] = chunk_rows * i + j;

        rmm::device_uvector<float> unified_buf(
            chunk_rows * (num_features + 1),
            raft_hdl.get_stream());

        for (size_t j = 0; j <= num_features; ++j) {
            raft::update_device(
                unified_buf.element_ptr(chunk_rows * j),
                &host_buf[0],
                chunk_rows,
                raft_hdl.get_stream());
        }
        raft_hdl.get_stream().synchronize();

        std::cout << unified_buf.element(chunk_rows - 8, raft_hdl.get_stream())
                  << " "
                  << unified_buf.element(2 * chunk_rows - 8, raft_hdl.get_stream())
                  << std::endl;

        float intercept = 0;
        rmm::device_uvector<float> coefs(
            num_features + 1,
            raft_hdl.get_stream());
        ML::GLM::olsFit(
            raft_hdl,
            unified_buf.element_ptr(0), // features
            chunk_rows,
            num_features,
            unified_buf.element_ptr(chunk_rows * num_features), // labels
            coefs.data(), // coefficients outparam
            &intercept,   // intercept outparam
            true,         // fit intercept
            false,        // normalize
            0);
        coefs.set_element(num_features, intercept, raft_hdl.get_stream());

        for (size_t j = 0; j <= num_features; ++j) {
            float avg_coef =
                total_rows ? (total_rows *
                                  out_coefs.element(j, raft_hdl.get_stream()) +
                              chunk_rows *
                                  coefs.element(j, raft_hdl.get_stream())) /
                                 (total_rows + chunk_rows)
                           : coefs.element(j, raft_hdl.get_stream());
            out_coefs.set_element_async(j, avg_coef, raft_hdl.get_stream());
        }
        total_rows += chunk_rows;
        std::cout << "\033[35mCuML processed \033[33m" << chunk_rows
                  << "\033[35m rows and produced \033[33m"
                  << log_weights(coefs, raft_hdl.get_stream())
                  << "\033[35m\n\ttotal: \033[33m" << total_rows
                  << "\033[35m rows, avg coefs: \033[33m"
                  << log_weights(out_coefs, raft_hdl.get_stream())
                  << "\033[m\n\n";
    }
    raft_hdl.get_stream().synchronize();
    return 0;
}