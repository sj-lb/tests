#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <nlohmann/json.hpp>
#include "minio/minio.h"   // MinIO C++ SDK
#include "avro/Compiler.hh"
#include "avro/DataFile.hh"
#include "avro/Generic.hh"
#include "avro/Specific.hh"
using json = nlohmann::json;
// ====== Config ======
const std::string ENDPOINT = "192.168.5.82:9000";
const std::string ACCESS_KEY = "admin";
const std::string SECRET_KEY = "password";
const std::string BUCKET = "warehouse";
const std::string TABLE_PATH = "wh/my_namespace/my_table/metadata/00001-1234567890123.metadata.json";
const long long TARGET_SNAPSHOT_ID = 659779950866775480LL;
// Helper: download object from MinIO into string
std::string downloadFromMinIO(minio::s3::Client& client, const std::string& object) {
    minio::s3::GetObjectArgs args;
    args.bucket = BUCKET;
    args.object = object;
    std::stringstream buffer;
    auto resp = client.GetObject(args, [&](minio::http::DataFunctionArgs args) {
        buffer.write(reinterpret_cast<const char*>(args.data), args.length);
    });
    if (!resp) {
        throw std::runtime_error("Failed to download " + object + " : " + resp.Error().String());
    }
    return buffer.str();
}
int main() {
    try {
        // Step 1: connect to MinIO
        minio::s3::BaseUrl baseUrl(ENDPOINT);
        minio::creds::StaticProvider provider(ACCESS_KEY, SECRET_KEY, "");
        minio::s3::Client client(baseUrl, &provider, minio::s3::Region("us-east-1"), true);
        // Step 2: download metadata.json
        std::cout << "Downloading table metadata: " << TABLE_PATH << std::endl;
        std::string metadataStr = downloadFromMinIO(client, TABLE_PATH);
        json tableMeta = json::parse(metadataStr);
        // Step 3: find target snapshot
        std::string manifestListPath;
        for (auto& snapshot : tableMeta["snapshots"]) {
            long long snapshotId = snapshot["snapshot-id"].get<long long>();
            if (snapshotId == TARGET_SNAPSHOT_ID) {
                std::cout << "Found Snapshot ID: " << snapshotId << std::endl;
                std::cout << "Timestamp: " << snapshot["timestamp-ms"] << std::endl;
                manifestListPath = snapshot["manifest-list"];
                break;
            }
        }
        if (manifestListPath.empty()) {
            std::cerr << "Snapshot not found!" << std::endl;
            return 1;
        }
        std::cout << "Manifest list path: " << manifestListPath << std::endl;
        // Step 4: download manifest list Avro
        std::string manifestListData = downloadFromMinIO(client, manifestListPath);
        // Save to local temp file for avro-cpp reader
        std::string localFile = "/tmp/manifest-list.avro";
        std::ofstream out(localFile, std::ios::binary);
        out << manifestListData;
        out.close();
        // Step 5: read Avro manifest list file
        avro::DataFileReader<avro::GenericDatum> reader(localFile);
        const avro::ValidSchema& schema = reader.readerSchema();
        std::cout << "\nManifest Files in Snapshot:" << std::endl;
        while (reader.hasMore()) {
            avro::GenericDatum datum(schema);
            reader.read(datum);
            if (datum.type() == avro::AVRO_RECORD) {
                const avro::GenericRecord& record = datum.value<avro::GenericRecord>();
                std::string manifestPath = record.field("manifest_path").value<std::string>();
                long long length = record.field("manifest_length").value<long long>();
                std::cout << " -> Manifest file: " << manifestPath
                          << " (length: " << length << " bytes)" << std::endl;
            }
        }
        reader.close();
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }
    return 0;
}