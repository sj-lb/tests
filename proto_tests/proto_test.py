# python3 -m grpc_tools.protoc proto_test.proto -I. --python_out=. --grpc_python_out=.

import grpc
import proto_test_pb2
import proto_test_pb2_grpc

if __name__ == '__main__':
    channel = grpc.insecure_channel('localhost:50052')  # Replace with the server address

    # Create a stub (client) for the service
    stub = proto_test_pb2_grpc.BasicRpcStub(channel)  # Replace with the actual service name

    # Define the request message
    request = proto_test_pb2.request()  # Replace with the actual request message type
    request.size = 8

    # Make the gRPC call
    response = stub.regRpc(request)  # Replace with the actual method name

    # Process the response
    print(response.offset)  # Access the response fields

    # Close the channel
    channel.close()