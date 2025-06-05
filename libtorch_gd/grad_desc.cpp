// g++ -g grad_desc.cpp\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include/torch/csrc/api/include\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -lc10 -ltorch -ltorch_cpu\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib64

#include <iostream>
#include <vector>
#include <torch/torch.h>
#include <fstream>
#include <string>

// Helper function to load data in chunks (handles large datasets)
std::pair<torch::Tensor, torch::Tensor> load_data_chunk(
        const std::string& data_file,
        int chunk_size,
        int start_row,
        int num_features) {
    std::vector<std::vector<double>> features_chunk;
    std::vector<double> labels_chunk;

    std::ifstream file(data_file);
    std::string line;

    // Skip rows until the starting point
    for (int i = 0; i < start_row; ++i) {
        std::getline(file, line);
        if (file.eof()) return {{}, {}}; // Handle end of file
    }

    for (int i = 0; i < chunk_size; ++i) {
        if (std::getline(file, line)) {
            std::vector<double> row_features;
            // if (!(i % 100))
            //     std::cout << "\033[36mline \033[33;1m" << i
            //               << "\033[36m: \033[33;1m" << line << "\033[m\n";
            std::stringstream ss(line);
            std::string value;
            char delimiter = ','; // Adjust delimiter if needed

            // Assuming the last value in the line is the label
            int feature_count = 0;
            while (std::getline(ss, value, delimiter)) {
                if (feature_count == num_features) { // Assuming 10 features, adjust accordingly.
                    try {
                        labels_chunk.push_back(std::stof(value));
                    } catch (const std::invalid_argument& e) {
                        std::cerr << "Error converting label to double: " << e.what() << std::endl;
                        return {{}, {}};
                    }
                } else {
                    try {
                        row_features.push_back(std::stof(value));
                    } catch (const std::invalid_argument& e) {
                        std::cerr << "Error converting feature to double: " << e.what() << std::endl;
                        return {{}, {}};
                    }
                }
                feature_count++;
            }
            features_chunk.push_back(row_features);
        } else {
            break; // End of file
        }
    }
    file.close();

    if (features_chunk.empty()) return {{}, {}}; // No data read

    int num_samples = features_chunk.size();
    // int num_features = features_chunk[0].size(); // Check for empty lines

    auto features = torch::zeros({num_samples, num_features});
    auto labels = torch::zeros({num_samples});

    for (int i = 0; i < num_samples; ++i) {
        for (int j = 0; j < num_features; ++j) {
            features[i][j] = features_chunk[i][j];
        }
        labels[i] = labels_chunk[i];
    }

    return {features, labels};
}

int main() {
    // Example usage:
    std::string data_file = "/home/johnny/git/sj/libtorch_gd/sqa_train_data.csv"; // Replace with your data file
    int num_features = 1; // Number of features
    int output_size = 1; // Number of output units (e.g., 1 for regression)
    int chunk_size = 1'000'000; // Adjust chunk size based on available memory
    double learning_rate = 0.001;
    int num_epochs = 100'000;

    // Check if the data file exists
    std::ifstream file_check(data_file);
    if (!file_check.good()) {
        std::cerr << "Error: Data file '" << data_file << "' not found." << std::endl;
        return 1;
    }
    file_check.close();

    // torch::Device device(torch::kCPU); // Use CPU for large datasets

    // Define the model
    torch::nn::Linear model(num_features, output_size);
    // model->weight.data().fill_(1);
    // model->bias.data().fill_(0);
    // model->to(device);

    // Define the loss function and optimizer
    torch::nn::MSELoss criterion; // For regression
    torch::optim::Adam optimizer(model->parameters(), learning_rate);

    // Training loop with data loading in chunks
    int start_row = 0;
    double prev_loss = 10.0;
    double epoch_loss = 0.0;
    double threshold = 0.000'001;
    int epoch = 0;
    // torch::Tensor loss;
    // while (prev_loss - epoch_loss > threshold) {
    while (epoch < num_epochs) {
        optimizer.zero_grad();
        while (true) {
            auto [features, labels] = load_data_chunk(
                data_file,
                chunk_size,
                start_row,
                num_features);
            if (features.size(0) == 0) break; // No more data

            // features = features.to(device);
            // labels = labels.to(device);

            // Forward pass
            torch::Tensor preds = model->forward(features);
            torch::Tensor loss = criterion(preds, labels.reshape({-1,1})); // Reshape labels if needed
            prev_loss = epoch_loss;
            epoch_loss = loss.item<double>();
            if (!epoch)
                prev_loss = epoch_loss + 2 * threshold; // ensure more than 1 run

            // Backward pass and optimization
            loss.backward();
            // std::cout << 

            start_row += chunk_size;
        }
        std::cout << "\033[36mEpoch \033[33m" << epoch
                  << "\033[36m all chunks processed.\ncoefs before step: \033[33m"
                  << model->weight.item<double>() << ", "
                  << model->bias.item<double>() << "\n\033[36mgrads: \033[33m";
        for (const auto& param : model->parameters())
            std::cout << param.grad().cpu().item<double>() << ", ";
        std::cout << std::endl;
        optimizer.step();
        std::cout << "\033[36mcoefs after step: \033[33m" << model->weight.item<double>()
                  << ", " <<  model->bias.item<double>() << "\033[m\n\n";
            // if (!(epoch % 100)){

        // std::cout << "Epoch [" << epoch + 1 << "/" << num_epochs << "], Loss: " << loss.item<double>() << std::endl;
        // std::cout << "weight: " << model->weight.item<double>() << " bias: " << model->bias.item<double>() << std::endl;
            // }
        start_row = 0; // Reset for the next epoch
        epoch++;
    }

    std::cout << "Training finished!" << std::endl;
    std::cout << "weight: " << model->weight.item<double>() << " bias: " << model->bias.item<double>() << std::endl;

    // Save the trained model
    torch::save(model, "trained_model.pt");

    return 0;
}