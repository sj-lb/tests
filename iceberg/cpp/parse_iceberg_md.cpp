// g++ parse_iceberg_md.cpp -o r1.out\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libminiocpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libcurlpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libpugixml.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libINIReader.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libinih.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libssl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libcrypto.a\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include\
 -isystem /home/johnny/git/vcpkg/installed/x64-linux/include\
 -ldl -lz -lsnappy -lavrocpp -lz -lcurl -lpthread\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib

// g++ -g parse_iceberg_md.cpp -o r1_debug.out\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libminiocpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libcurlpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libpugixml.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libINIReader.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libinih.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libssl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libcrypto.a\
 -isystem /usr/local/sqream-prerequisites/versions/5.28/include\
 -isystem /home/johnny/git/vcpkg/installed/x64-linux/include\
 -ldl -lz -lsnappy -lavrocpp -lz -lcurl -lpthread\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib

#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <nlohmann/json.hpp>
#include <miniocpp/client.h>
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
const std::string TABLE_PATH = "my_namespace/my_table/metadata/snap-659779950866775480-1-6a41d1fe-ace2-4ec5-9620-d54679309e8b.avro";
const long long TARGET_SNAPSHOT_ID = 659779950866775480LL;

// Helper: download object from MinIO into string.
// NOTE: This has been updated to directly access the data member of the response
// object, which is required for this version of the SDK.
std::string downloadFromMinIO(minio::s3::Client& client, const std::string& object) {
    minio::s3::GetObjectArgs args;
    args.bucket = BUCKET;
    args.object = object;
    args.region = "us-east-1";
    args.datafunc = [](minio::http::DataFunctionArgs args) -> bool {
            // std::cout << args.datachunk;
            std::cout << "BLA\n";
            return true;
        };

    std::cout << "BLUE\n";
    minio::s3::GetObjectResponse resp;
    try
    {
        minio::s3::GetObjectResponse resp = client.GetObject(args);
    }
    catch(const std::exception& e)
    {
        std::cerr << e.what() << '\n';
    }

    std::cout << "SHOE\n";
    if (!resp) {
        throw std::runtime_error("Failed to download " + object + " : " + resp.Error().String());
    }

    return resp.data;
}

int main() {
    try {
        // Step 1: connect to MinIO
        // NOTE: The Client constructor signature has changed. The `Region` argument
        // is no longer used this way. The client infers the region from the endpoint
        // or it can be set via an `Options` struct.
        minio::s3::BaseUrl baseUrl(ENDPOINT);
        minio::creds::StaticProvider provider(ACCESS_KEY, SECRET_KEY, "");
        minio::s3::Client client(baseUrl, &provider);

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
        // NOTE: The Avro DataFileReader constructor requires a C-style string,
        // so we use .c_str() to convert the std::string.
        avro::DataFileReader<avro::GenericDatum> reader(localFile.c_str());
        const avro::ValidSchema& schema = reader.readerSchema();

        std::cout << "\nManifest Files in Snapshot:" << std::endl;
        // NOTE: The `hasMore()` method has been replaced. The `read()` method now
        // returns true as long as there is more data to read.
        avro::GenericDatum datum(schema);
        while (reader.read(datum)) {
            if (datum.type() == avro::AVRO_RECORD) {
                const avro::GenericRecord& record = datum.value<avro::GenericRecord>();
                std::string manifestPath = record.field("manifest_path").value<std::string>();
                long long length = record.field("manifest_length").value<long long>();
                std::cout << " -> Manifest file: " << manifestPath
                          << " (length: " << length << " bytes)" << std::endl;
            }
        }

        // NOTE: reader.close() is not needed as the destructor handles it.
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << std::endl;
        return 1;
    }
    return 0;
}