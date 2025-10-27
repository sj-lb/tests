// 

#include <iostream>
#include <exception>

#include <avro/Compiler.hh>
#include <avro/DataFile.hh>
#include <avro/Generic.hh>

std::unique_ptr<avro::DataFileReader<avro::GenericDatum>> create_avro_reader(
        const std::string& file_path,
        std::shared_ptr<std::istream> avroIStream) {
    try {
        return std::unique_ptr<avro::DataFileReader<avro::GenericDatum>>(
            new DataFileReader<avro::GenericDatum>(
                avro::istreamInputStream(*avroIStream)));
    }
    catch (const std::exception& e) {
        std::cerr << "\033[31mcreate_avro_reader(\033[33;1m" << file_path
                  << "\033[0;31m) Exception: \033[m" << e.what() << std::endl;
        throw e;
    }
}

void process(const std::string& file_path)
{
    std::shared_ptr<std::istream> m_avroIStream =
        std::make_shared<AvroIStream>(file_path);

    std::unique_ptr<avro::DataFileReader<avro::GenericDatum>> avro_reader =
        create_avro_reader(file_path, m_avroIStream);

    // Use schema file if specified, otherwise read from data file.
    avro::ValidSchema m_avro_schema = avro_reader->dataSchema();

    // create generic data type from schema
    avro::GenericDatum datum(m_avro_schema);

    try {
        avro::GenericRecord& r = datum.value<avro::GenericRecord>();
        while (avro_reader->read(datum)) {
            do {
                if (datum.type() == avro::AVRO_RECORD) {
                    r = datum.value<avro::GenericRecord>();
                    std::cout << "\033[34;1mread row: \033[33m" << r << "\033[m\n";
                    m_rows.push_back(r);
                }
            } while (m_rows.size() <
                         m_storage_worker->m_chunk_size -
                             m_chunks_dispatcher->get_curr_chunk_row_count() &&
                     avro_reader->read(datum));

            if (m_chunks_dispatcher->get_curr_chunk_row_count() == 0) {
                init();
            }

            // Parse read rows
            parse_read_rows();

            // Check error
            if (m_storage_worker->m_error_tolerance->error_tolerance_exceeded())
            {
                processing_result = ERROR_TOLERANCE_EXCEEDED;
                break;
            }

            const auto total_number_of_error_rows = std::count_if(
                m_error_rows_to_skip.cbegin(),
                m_error_rows_to_skip.cend(),
                [](bool is_error_row) { return is_error_row; });

            if (total_number_of_error_rows)
                remove_error_rows();

            const auto total_valid_rows =
                m_rows.size() - total_number_of_error_rows;
            // Add to dispatcher
            processing_result =
                m_chunks_dispatcher->add_row_count_to_and_dispatch_if_full(
                    total_valid_rows);
            if (processing_result != KEEP_PROCESSING) {
                break;
            }

            m_row_offset += total_valid_rows;
            m_rows.clear();
        }
        while (avro_reader->read(datum));
    }
    catch (const std::exception& e) {
        std::cerr << "\033[31mError while reading avro file \033[33;1m"
                  << file_path << "\033[0;31m: \033[m" << e.what() << std::endl;
        throw e;
    }

    m_avroIStream.reset();
    return processing_result;
}

int main()