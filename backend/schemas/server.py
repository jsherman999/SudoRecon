"""Server-related Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.server import ServerStatus


class ServerBase(BaseModel):
    """Base server schema."""

    hostname: str = Field(max_length=255, description="Server hostname")
    fqdn: str = Field(max_length=512, description="Fully qualified domain name")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    domain: Optional[str] = Field(default=None, max_length=255, description="Domain name")
    os_version: Optional[str] = Field(default=None, max_length=128, description="OS version")


class ServerCreate(ServerBase):
    """Schema for creating a server."""

    status: ServerStatus = Field(default=ServerStatus.ACTIVE)
    metadata: Dict = Field(default_factory=dict)


class ServerUpdate(BaseModel):
    """Schema for updating a server."""

    hostname: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None)
    os_version: Optional[str] = Field(default=None)
    status: Optional[ServerStatus] = Field(default=None)
    metadata: Optional[Dict] = Field(default=None)


class ServerResponse(ServerBase):
    """Schema for server response."""

    id: int
    status: ServerStatus
    last_scan_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerGroupBase(BaseModel):
    """Base server group schema."""

    name: str = Field(max_length=255, description="Group name")
    description: Optional[str] = Field(default=None, description="Group description")


class ServerGroupCreate(ServerGroupBase):
    """Schema for creating a server group."""

    pass


class ServerGroupUpdate(BaseModel):
    """Schema for updating a server group."""

    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)


class ServerGroupResponse(ServerGroupBase):
    """Schema for server group response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerGroupWithMembers(ServerGroupResponse):
    """Server group with member count."""

    member_count: int = Field(description="Number of servers in group")
    servers: List[ServerResponse] = Field(default_factory=list)


class AddGroupMembersRequest(BaseModel):
    """Request to add servers to a group."""

    server_ids: List[int] = Field(description="List of server IDs to add")
