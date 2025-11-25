"""Pydantic schemas for API."""

from .common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from .job import (
    ScanFileRequest,
    ScanGroupRequest,
    ScanJobDetail,
    ScanJobResponse,
    ScanOptions,
    ScanSingleRequest,
)
from .log import (
    LogSearchParams,
    LogStats,
    SudoLogCreate,
    SudoLogResponse,
    SudoLogWithServer,
)
from .provision import (
    BulkProvisionRequest,
    BulkProvisionResponse,
    JITAccessRequest,
    JITAccessResponse,
    ProvisionCreate,
    ProvisionResponse,
    ProvisionUpdate,
    ProvisionWithServer,
    RevokeProvisionRequest,
)
from .server import (
    AddGroupMembersRequest,
    ServerCreate,
    ServerGroupCreate,
    ServerGroupResponse,
    ServerGroupUpdate,
    ServerGroupWithMembers,
    ServerResponse,
    ServerUpdate,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # Server
    "ServerCreate",
    "ServerUpdate",
    "ServerResponse",
    "ServerGroupCreate",
    "ServerGroupUpdate",
    "ServerGroupResponse",
    "ServerGroupWithMembers",
    "AddGroupMembersRequest",
    # Log
    "SudoLogCreate",
    "SudoLogResponse",
    "SudoLogWithServer",
    "LogSearchParams",
    "LogStats",
    # Job
    "ScanSingleRequest",
    "ScanGroupRequest",
    "ScanFileRequest",
    "ScanOptions",
    "ScanJobResponse",
    "ScanJobDetail",
    # Provision
    "ProvisionCreate",
    "ProvisionUpdate",
    "ProvisionResponse",
    "ProvisionWithServer",
    "JITAccessRequest",
    "JITAccessResponse",
    "BulkProvisionRequest",
    "BulkProvisionResponse",
    "RevokeProvisionRequest",
]
