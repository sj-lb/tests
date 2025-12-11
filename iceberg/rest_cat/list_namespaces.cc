/*
 * COMPILATION INSTRUCTIONS for iceberg-cpp17 (C++17 compatible version)
 * 
 * Prerequisites:
 * - iceberg-cpp17 must be built and installed
 * - GCC 7+ or Clang 5+ (for C++17 support)
 * 
 * Method 1 - Build iceberg-cpp17 and this example:
 * 
 * # Build and install iceberg-cpp17
 * cd /home/johnny/git/sqream/iceberg-cpp17
 * cmake -S . -B build -G Ninja \
 *   -DCMAKE_INSTALL_PREFIX=/home/johnny/git/sqream/iceberg-cpp17/install \
 *   -DICEBERG_BUILD_STATIC=ON \
 *   -DICEBERG_BUILD_REST=ON \
 *   -DICEBERG_BUILD_TESTS=OFF \
 *   -DCMAKE_BUILD_TYPE=Release
 * cmake --build build
 * cmake --install build
 * 
 * # Compile this example
 * cd /home/johnny/git/sj/iceberg/rest_cat
 * /usr/local/sqream-prerequisites/versions/6.04/bin/g++ -std=c++17 \
 *   -I/home/johnny/git/sqream/iceberg-cpp17/install/include \
 *   -I/usr/local/sqream-prerequisites/versions/6.04/include \
 *   list_namespaces.cc \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_rest.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_bundle.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_vendored_arrow.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_vendored_parquet.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_vendored_avrocpp.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_vendored_croaring.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libiceberg_vendored_cpr.a \
 *   /home/johnny/git/sqream/iceberg-cpp17/install/lib64/libarrow_bundled_dependencies.a \
 *   /usr/local/sqream-prerequisites/versions/6.04/lib/libnanoarrow.a \
 *   -L/usr/local/sqream-prerequisites/versions/6.04/lib64 \
 *   -lfmt -lcurl -lssl -lcrypto -lz -lpthread -ldl \
 *   -o list_namespaces
 * 
 * Method 2 - Using CMake:
 * 
 * Create a CMakeLists.txt in this directory:
 * 
 * cmake_minimum_required(VERSION 3.20)
 * project(list_namespaces)
 * set(CMAKE_CXX_STANDARD 17)
 * set(CMAKE_PREFIX_PATH "/home/johnny/git/sqream/iceberg-cpp17/install")
 * find_package(iceberg CONFIG REQUIRED)
 * add_executable(list_namespaces list_namespaces.cc)
 * target_link_libraries(list_namespaces PRIVATE 
 *   iceberg::iceberg_static 
 *   iceberg::iceberg_rest_static)
 * 
 * Then build with:
 *   cmake -B build && cmake --build build
 * 
 * USAGE:
 *   ./list_namespaces <rest_catalog_uri>
 * 
 * Examples:
 *   ./list_namespaces http://localhost:8181
 *   ./list_namespaces https://catalog.example.com:8181
 */

#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>

#include "iceberg/catalog/rest/catalog_properties.h"
#include "iceberg/catalog/rest/rest_catalog.h"
#include "iceberg/table_identifier.h"

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "Usage: " << argv[0] << " <rest_catalog_uri>" << std::endl;
    std::cerr << "Example: " << argv[0] << " http://localhost:8181" << std::endl;
    return 1;
  }

  const std::string catalog_uri = argv[1];

  // Create catalog configuration properties
  std::unordered_map<std::string, std::string> properties;
  properties["uri"] = catalog_uri;
  properties["name"] = "rest_catalog";
  
  // Optional: Add authentication headers if needed
  // properties["header.Authorization"] = "Bearer <token>";
  // properties["warehouse"] = "/path/to/warehouse";
  // properties["prefix"] = "v1";

  auto config = iceberg::rest::RestCatalogProperties::FromMap(properties);
  if (!config) {
    std::cerr << "Failed to create catalog properties" << std::endl;
    return 1;
  }

  // Create the REST catalog instance
  auto catalog_result = iceberg::rest::RestCatalog::Make(*config);
  if (!catalog_result.has_value()) {
    std::cerr << "Failed to create REST catalog: " 
              << catalog_result.error().message << std::endl;
    return 1;
  }

  auto catalog = std::move(catalog_result.value());
  std::cout << "Successfully connected to catalog: " << catalog->name() << std::endl;

  // List all top-level namespaces (empty namespace means root level)
  iceberg::Namespace root_namespace{.levels = {}};
  
  auto namespaces_result = catalog->ListNamespaces(root_namespace);
  if (!namespaces_result.has_value()) {
    std::cerr << "Failed to list namespaces: " 
              << namespaces_result.error().message << std::endl;
    return 1;
  }

  auto namespaces = std::move(namespaces_result.value());

  if (namespaces.empty()) {
    std::cout << "No namespaces found in the catalog." << std::endl;
  } else {
    std::cout << "\nFound " << namespaces.size() << " namespace(s):" << std::endl;
    std::cout << "----------------------------------------" << std::endl;
    
    for (const auto& ns : namespaces) {
      // Print namespace as a dot-separated string
      std::cout << "  ";
      for (size_t i = 0; i < ns.levels.size(); ++i) {
        if (i > 0) std::cout << ".";
        std::cout << ns.levels[i];
      }
      std::cout << std::endl;
      
      // Optionally, list sub-namespaces (uncomment if needed)
      /*
      auto sub_namespaces_result = catalog->ListNamespaces(ns);
      if (sub_namespaces_result.has_value() && !sub_namespaces_result.value().empty()) {
        std::cout << "    (has " << sub_namespaces_result.value().size() 
                  << " sub-namespace(s))" << std::endl;
      }
      */
    }
    std::cout << "----------------------------------------" << std::endl;
  }

  // Optionally, check if a specific namespace exists
  // iceberg::Namespace test_ns{.levels = {"test_namespace"}};
  // auto exists_result = catalog->NamespaceExists(test_ns);
  // if (exists_result.has_value()) {
  //   std::cout << "Namespace 'test_namespace' exists: " 
  //             << (exists_result.value() ? "yes" : "no") << std::endl;
  // }

  return 0;
}
