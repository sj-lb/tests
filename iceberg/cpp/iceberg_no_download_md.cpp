// g++ -std=c++17 iceberg_no_download_md.cpp -o r3.out\
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

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <miniocpp/client.h>   // MinIO C++ SDK

std::string readAvroFromMinIO(
        minio::s3::Client& client,
        const std::string& bucket,
        const std::string& object) {
    minio::s3::GetObjectArgs args;
    std::string out;
    args.bucket = bucket;
    args.object = object;

    // The datafunc lambda is called for each chunk of data received.
    // This is where you would process the Avro data directly.
    // For this example, we simply print the chunk size.
    args.datafunc = [&out](minio::http::DataFunctionArgs dfargs) -> bool {
        std::cout << "Received data chunk of size: " << dfargs.datachunk.size() << " bytes." << std::endl;
        out = std::move(dfargs.datachunk);
        // This is the point where you would feed the 'dfargs.datachunk'
        // to an Avro C++ library reader.
        // For example: my_avro_reader.read(dfargs.datachunk.data(), dfargs.datachunk.size());
        return true; // continue reading
    };

    minio::s3::GetObjectResponse resp = client.GetObject(args);
    if (!resp) {
        std::cerr << "GetObject failed: " << resp.Error().String() << std::endl;
        // It's a good practice to handle the error, but we'll return
        // to let the main function continue.
    } else {
        std::cout << "Successfully read object: " << object << " from bucket: " << bucket << std::endl;
    }

    return out;
}

int main() {
    try {
        // Connect to MinIO
        minio::s3::BaseUrl url("http://192.168.5.82:9000", false);
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
        
        // Define the object to read
        std::string object = "my_namespace/my_table/metadata/snap-659779950866775480-1-6a41d1fe-ace2-4ec5-9620-d54679309e8b.avro";
        std::cout << "Starting stream read for manifest: " << object << std::endl;

        // Call the new function to read the object in a streaming fashion
        // This replaces the old download and file-saving logic.
        std::string content = readAvroFromMinIO(client, bucket, object);

        std::cout << "\033[34;1mprinting avro content:\033[33m\n" << content
                  << "\033[m\n";

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}