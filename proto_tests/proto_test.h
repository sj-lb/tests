#ifndef __BASIC_RPC__
#define __BASIC_RPC__

#include "proto_test.pb.h"
#include "proto_test.grpc.pb.h"

namespace basic_rpc {
class BasicRpcImpl final : public BasicRpc::Service
{
public:
    grpc::Status regRpc(grpc::ServerContext* context, const request* req, response* res);
    grpc::Status resRpc(grpc::ServerContext* context, const response* res, request* req);
};
} // namespace basic_rpc
#endif // __BASIC_RPC__
