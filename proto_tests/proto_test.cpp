// protoc proto_test.proto -I.\
 --cpp_out=. --grpc_out=. --plugin=protoc-gen-grpc=`which grpc_cpp_plugin`

// g++ -g -o proto_test.out proto_test.cpp proto_test.pb.cc proto_test.grpc.pb.cc\
 -isystem /usr/local/sqream-prerequisites/versions/5.24/include\
 -lprotobuf -lgrpc++\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib\
 -L/usr/local/sqream-prerequisites/versions/5.24/lib64

#include <iostream>
#include <grpcpp/grpcpp.h>

#include "proto_test.h"

size_t alloc = 0;

namespace basic_rpc {

grpc::Status BasicRpcImpl::regRpc(grpc::ServerContext* context, const request* req, response* res) {
    std::cout << "\033[35mServer got size: \033[33m" << req->size() << "\033[m\n";
    res->set_offset(alloc);
    alloc += req->size();
    return grpc::Status::OK;
}
grpc::Status BasicRpcImpl::resRpc(grpc::ServerContext* context, const response* res, request* req) {
    std::cout << "\033[35mServer got offset: \033[33m" << res->offset() << "\033[m\n";
    req->set_size(0);
    alloc -= 8;
    return grpc::Status::OK;
}
} // namespace basic_rpc

int main() {
    std::string server_address("0.0.0.0:50052");
    basic_rpc::BasicRpcImpl service;

    grpc::ServerBuilder builder;
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
    std::cout << "Server listening on " << server_address << std::endl;
    server->Wait();

    return 0;
}