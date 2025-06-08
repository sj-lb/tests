// g++ -c -E\
 -I/usr/local/sqream-prerequisites/versions/5.24/include/apr-1\
 -I/usr/include\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/ghc-8.6.5\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/ghc-8.6.5/include\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/extras/CUPTI/include -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/gcc/x86_64-unknown-linux-gnu/11.1.0/plugin/include -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/gcc/x86_64-unknown-linux-gnu/11.1.0/plugin/include/c-family -isystem /usr/local/sqream-prerequisites/versions/5.24/aws-cpp-sdk-s3/include -isystem /usr/local/sqream-prerequisites/versions/5.24/aws-cpp-sdk-core/include -isystem /usr/local/sqream-prerequisites/versions/5.24/build/.deps/install/include -isystem /usr/local/sqream-prerequisites/versions/5.24/src -isystem /usr/local/sqream-prerequisites/versions/5.24/src/cudf -I/usr/local/sqream-prerequisites/package-install/python-3.9.13-8.5.0_alt/lib/python3.9/site-packages/numpy/core/include/ -I/usr/local/sqream-prerequisites/package-install/python-3.9.13-8.5.0_alt/include/python3.9 -I/usr/local/sqream-prerequisites/versions/5.24/samples/common/inc/ -isystem /usr/local/sqream-prerequisites/versions/5.24/include/torch/csrc/api/include -Ibuild/remote-pkgs/protobuffers-build/src/main/protobuf -march=native -mtune=native -pipe -std=c++17 -fconcepts -fmessage-length=0 -fPIC -fsigned-char -fstack-protector-all -DFMT_HEADER_ONLY=1 -DLIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -DSPDLOG_FMT_EXTERNAL -DUSE_C10D_GLOO -DUSE_DISTRIBUTED -DUSE_RPC -DUSE_TENSORPIPE -g3 -DDEBUG -DCUDA=CUDA  -Wextra -Wno-variadic-macros -Wall -Werror=cast-qual -Werror=return-type -Werror=init-self -Werror=format -Werror=uninitialized -Werror=unused-result -Wno-error=cpp -Werror -pthread -D LIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -o build/cpp/runtime/chunk_producers/LinearRegressionTrain.i cpp/runtime/chunk_producers/LinearRegressionTrain.cpp
// g++ -c -Icuda -Icpp -Ilicensing -I/usr/local/sqream-prerequisites/versions/5.24/include/apr-1/ -Idist/build/Database/Sqream/Compile/ -I/usr/include/ -isystem /usr/local/sqream-prerequisites/versions/5.24/include -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/ghc-8.6.5 -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/ghc-8.6.5/include -isystem /usr/local/sqream-prerequisites/versions/5.24/extras/CUPTI/include -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/gcc/x86_64-unknown-linux-gnu/11.1.0/plugin/include -isystem /usr/local/sqream-prerequisites/versions/5.24/lib/gcc/x86_64-unknown-linux-gnu/11.1.0/plugin/include/c-family -isystem /usr/local/sqream-prerequisites/versions/5.24/aws-cpp-sdk-s3/include -isystem /usr/local/sqream-prerequisites/versions/5.24/aws-cpp-sdk-core/include -isystem /usr/local/sqream-prerequisites/versions/5.24/build/.deps/install/include -isystem /usr/local/sqream-prerequisites/versions/5.24/src -isystem /usr/local/sqream-prerequisites/versions/5.24/src/cudf -I/usr/local/sqream-prerequisites/package-install/python-3.9.13-8.5.0_alt/lib/python3.9/site-packages/numpy/core/include/ -I/usr/local/sqream-prerequisites/package-install/python-3.9.13-8.5.0_alt/include/python3.9 -I/usr/local/sqream-prerequisites/versions/5.24/samples/common/inc/ -isystem /usr/local/sqream-prerequisites/versions/5.24/include/torch/csrc/api/include -Ibuild/remote-pkgs/protobuffers-build/src/main/protobuf -march=native -mtune=native -pipe -std=c++17 -fconcepts -fmessage-length=0 -fPIC -fsigned-char -fstack-protector-all -DFMT_HEADER_ONLY=1 -DLIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -DSPDLOG_FMT_EXTERNAL -DUSE_C10D_GLOO -DUSE_DISTRIBUTED -DUSE_RPC -DUSE_TENSORPIPE -g3 -DDEBUG -DCUDA=CUDA  -Wextra -Wno-variadic-macros -Wall -Werror=cast-qual -Werror=return-type -Werror=init-self -Werror=format -Werror=uninitialized -Werror=unused-result -Wno-error=cpp -Werror -pthread -D LIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -o build/cpp/runtime/chunk_producers/LinearRegressionTrain.o cpp/runtime/chunk_producers/LinearRegressionTrain.cpp

// g++ -g logreg.cpp -o test.out\
 -fconcepts -fmessage-length=0 -fPIC -fsigned-char -fstack-protector-all\
 -DUSE_TENSORPIPE -DFMT_HEADER_ONLY=1 -DSPDLOG_FMT_EXTERNAL -DUSE_C10D_GLOO\
 -DLIBCUDACXX_ENABLE_EXPERIMENTAL_MEMORY_RESOURCE -DUSE_DISTRIBUTED -DUSE_RPC\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -ldl -lrt -lcuda -lcudart -lnvToolsExt -ltreelite -lraft -lcumlprims_mg -lcuml++\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib64

#include <iostream>
#include <cuml/linear_model/glm.hpp>
#include <raft/core/handle.hpp>
#include <rmm/device_uvector.hpp>

static constexpr size_t bias = 1;

static std::string log_weights(std::vector<double> weights)
{
    std::string ret("[");
    for (double w : weights)
        ret += std::to_string(w) + ", ";
    return ret.substr(0, ret.length() - 2) + "]";
}

static std::string log_weights(const rmm::device_uvector<double>& coefs)
{
    std::string ret("[");
    for (size_t i = 0; i < coefs.size(); ++i)
        ret += std::to_string(coefs.element(i, coefs.stream())) +
               (i == coefs.size() - 1 ? "]" : ", ");
    return ret;
}

template<typename T>
std::vector<T> parse_csv_line(const std::string& line) {
    std::vector<T> row_data;
    std::string cell;
    std::istringstream line_stream(line);

    while (std::getline(line_stream, cell, ',')) {
        try {
            row_data.push_back(std::stod(cell)); // Convert string to float
        } catch (const std::invalid_argument& e) {
            std::cerr << "Invalid argument during CSV parsing: " << e.what() << std::endl;
            // Handle error, e.g., skip the value, throw, etc.
        } catch (const std::out_of_range& e) {
            std::cerr << "Out of range during CSV parsing: " << e.what() << std::endl;
            // Handle error
        }
    }
    return row_data;
}

template<typename T>
std::vector<T> read_csv(const std::string& filename, size_t& rows) {
    std::vector<T> ret;
    std::ifstream ifs(filename);
    if (!ifs.is_open()) {
        std::cerr << "Error: Could not open " << filename << std::endl;
        exit(1);
    }
    std::string line;
    while (std::getline(ifs, line)) {
        std::vector<T> row = parse_csv_line<T>(line);
        ret.insert(ret.end(), row.begin(), row.end());
        ++rows;
    }
    ifs.close();

    return ret;
}

std::vector<double> calculate_model_weights()
{
    // rmm::mr::set_current_device_resource(&RmmMemResource::getInstance());
    raft::handle_t raft_hdl;

    ML::GLM::qn_params params;
    params.loss = ML::GLM::QN_LOSS_LOGISTIC;
    params.penalty_l2 = 1e-3; // Learning rate
    params.max_iter = 1000;    // Max iterations
    params.change_tol = 1e-4; // Tolerance
    size_t num_classes = 2;   // only binary classification supported presently

    size_t rows = 0;
    size_t meh;
    std::vector<double> xdata(read_csv<double>("xtrain.csv", rows));
    size_t num_features = xdata.size() / rows;
    std::vector<double> model_weights(num_features + bias);
    rmm::device_uvector<double> features(rows * num_features, raft_hdl.get_stream());
    raft::update_device(features.data(), xdata.data(), rows * num_features, raft_hdl.get_stream());
    
    std::vector<double> ydata(read_csv<double>("ytrain.csv", meh));
    rmm::device_uvector<double> labels(rows, raft_hdl.get_stream());
    raft::update_device(labels.data(), ydata.data(), rows, raft_hdl.get_stream());

    raft_hdl.get_stream().synchronize();

    double intercept = 0.0;
    int epochs = 0;
    rmm::device_uvector<double> coefs(
        num_features + bias,
        raft_hdl.get_stream());
    ML::GLM::qnFit(
        raft_hdl,
        params,
        features.data(),
        false, // features is col major
        labels.data(),
        static_cast<int>(rows),
        static_cast<int>(num_features),
        static_cast<int>(num_classes),
        coefs.data(),
        &intercept,
        &epochs);
    for (size_t i = 0; i < model_weights.size(); i++)
        model_weights[i] = coefs.element(i, coefs.stream());
    // model_weights[model_weights.size() - 1] = intercept;
    raft_hdl.get_stream().synchronize();

    return model_weights;
}

int main() {
    std::vector<double> weights(calculate_model_weights());
    std::cout << "\033[34;1mcpp weights: \033[33m[";
    for (double d : weights)
        std::cout << d << ", ";
    std::cout << "\b\b]\033[m\n";

    return 0;
}