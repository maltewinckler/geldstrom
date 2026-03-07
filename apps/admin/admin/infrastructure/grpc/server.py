"""gRPC server factory."""

import grpc.aio

from admin.infrastructure.grpc.bank_directory_servicer import BankDirectoryServicer
from admin.infrastructure.grpc.generated.bank_directory_pb2_grpc import (
    add_BankDirectoryServiceServicer_to_server,
)
from admin.infrastructure.grpc.generated.key_validation_pb2_grpc import (
    add_KeyValidationServiceServicer_to_server,
)
from admin.infrastructure.grpc.key_validation_servicer import KeyValidationServicer


async def create_grpc_server(
    key_validation_servicer: KeyValidationServicer,
    bank_directory_servicer: BankDirectoryServicer,
    port: int = 50051,
) -> grpc.aio.Server:
    """Create and configure a gRPC server with all servicers.

    Args:
        key_validation_servicer: Servicer for key validation RPCs.
        bank_directory_servicer: Servicer for bank directory RPCs.
        port: Port to bind the server to. Defaults to 50051.

    Returns:
        Configured gRPC server (not yet started).
    """
    server = grpc.aio.server()
    add_KeyValidationServiceServicer_to_server(key_validation_servicer, server)
    add_BankDirectoryServiceServicer_to_server(bank_directory_servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    return server
