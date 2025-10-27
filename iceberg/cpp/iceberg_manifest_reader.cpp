// g++ -std=c++17 iceberg_manifest_reader.cpp -o r2.out\
 -isystem /home/johnny/git/vcpkg/installed/x64-linux/include\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libminiocpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libpugixml.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libcurlpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libcurl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libssl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libcrypto.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libz.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libINIReader.a\
 /home/johnny/git/vcpkg/installed/x64-linux/lib/libinih.a\
 -ldl -lz -lsnappy -lavrocpp -lpthread

// g++ -g -std=c++17 iceberg_manifest_reader.cpp -o r2_debug.out\
 -isystem /home/johnny/git/vcpkg/installed/x64-linux/include\
 -L/usr/local/sqream-prerequisites/versions/5.28/lib\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libminiocpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libpugixml.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libcurlpp.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libcurl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libssl.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libcrypto.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libz.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libINIReader.a\
 /home/johnny/git/vcpkg/installed/x64-linux/debug/lib/libinih.a\
 -ldl -lz -lsnappy -lavrocpp -lpthread

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <miniocpp/client.h>   // MinIO C++ SDK

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <miniocpp/client.h>   // MinIO C++ SDK
std::string downloadFromMinIO(minio::s3::Client& client,
                              const std::string& bucket,
                              const std::string& object) {
    std::stringstream buffer;
    minio::s3::GetObjectArgs args;
    args.bucket = bucket;
    args.object = object;
    // Capture buffer by reference so downloaded data is stored
    args.datafunc = [&](minio::http::DataFunctionArgs dfargs) -> bool {
        buffer.write(dfargs.datachunk.data(), dfargs.datachunk.size());
        return true; // continue reading
    };
    minio::s3::GetObjectResponse resp = client.GetObject(args);
    if (!resp) {
        std::cerr << "GetObject failed: " << resp.Error().String() << std::endl;
        return {};
    }
    return buffer.str();
}
int main() {
    try {
        // Connect to MinIO
        minio::s3::BaseUrl url("http://192.168.5.82:9000",false);  // adjust if inside container
        minio::creds::StaticProvider provider("admin", "password");
        minio::s3::Client client(url, &provider);
        //client.Debug(true);
        // List all buckets
        minio::s3::ListBucketsResponse listResp = client.ListBuckets();
        if (!listResp) {
            std::cerr << "Unable to list buckets: " << listResp.Error().String() << std::endl;
            return 1;
        }
        std::cout << "Buckets:\n";
        for (auto& b : listResp.buckets) {
            std::cout << " - " << b.name << " (created: "
                      << b.creation_date.ToHttpHeaderValue() << ")\n";
        }
        std::string bucket = "warehouse";
        // Check bucket existence
        minio::s3::BucketExistsArgs existsArgs;
        existsArgs.bucket = bucket;
        minio::s3::BucketExistsResponse existsResp = client.BucketExists(existsArgs);
        if (!existsResp) {
            std::cerr << "BucketExists failed: " << existsResp.Error().String() << std::endl;
            return 1;
        }
        std::cout << bucket << (existsResp.exist ? " exists\n" : " does not exist\n");
        // Download snapshot manifest
        std::string object = "my_namespace/my_table/metadata/snap-659779950866775480-1-6a41d1fe-ace2-4ec5-9620-d54679309e8b.avro";
        std::cout << "Downloading manifest: " << object << std::endl;
        std::string content = downloadFromMinIO(client, bucket, object);
        if (content.empty()) {
            std::cerr << "Failed to download manifest or it is empty\n";
            return 1;
        }
        // Save to file
        std::ofstream out("manifest.avro", std::ios::binary);
        out.write(content.data(), content.size());
        out.close();
        std::cout << "Saved manifest to manifest.avro (" << content.size() << " bytes)\n";
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}