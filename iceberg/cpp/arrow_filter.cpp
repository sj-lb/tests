#include <arrow/api.h>
#include <arrow/compute/api.h>
#include <arrow/dataset/api.h>

#include <iostream>

arrow::Status RunMain() {
    // 1. Create a simple Arrow Table to use as our dataset source
    auto f1 = arrow::field("int_col", arrow::int32());
    auto f2 = arrow::field("string_col", arrow::utf8());
    auto schema = arrow::schema({f1, f2});

    auto int_array = arrow::ArrayFromVector<arrow::int32>({1, 2, 3, 4, 5});
    auto string_array = arrow::ArrayFromVector<arrow::util::string_view>({"a", "b", "c", "d", "e"});

    auto table = arrow::Table::Make(schema, {int_array, string_array});

    // 2. Create a dataset from the table
    std::shared_ptr<arrow::dataset::Dataset> dataset;
    ARROW_ASSIGN_OR_RAISE(dataset, arrow::dataset::InMemoryDataset::Make(table));

    // 3. Define the filter expression. Here we filter for rows where 'int_col' > 2.
    auto int_col = arrow::compute::field_ref("int_col");
    auto literal = arrow::compute::literal(2);
    auto filter_expression = arrow::compute::greater(int_col, literal);

    // 4. Create the ScannerBuilder and apply the filter
    arrow::dataset::ScannerBuilder scanner_builder(dataset);
    ARROW_RETURN_NOT_OK(scanner_builder.Filter(filter_expression));

    // 5. Build the scanner and create the record batches
    ARROW_ASSIGN_OR_RAISE(auto scanner, scanner_builder.Finish());
    ARROW_ASSIGN_OR_RAISE(auto record_batches, scanner->ToVector());

    // 6. Print the results
    std::cout << "Filtered batches:" << std::endl;
    for (const auto& batch : record_batches) {
        std::cout << batch->ToString() << std::endl;
    }

    return arrow::Status::OK();
}

int main() {
    arrow::Status st = RunMain();
    if (!st.ok()) {
        std::cerr << "Error: " << st.ToString() << std::endl;
        return 1;
    }
    return 0;
}