"""Provision-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.models.provision import PrincipalType, ProvisionStatus


class ProvisionBase(BaseModel):
    """Base provision schema."""

    principal_type: PrincipalType
    principal_name: str = Field(max_length=512)
    sudo_rule: str
    is_jit: bool = False
    grant_start: Optional[datetime] = None
    grant_end: Optional[datetime] = None
    justification: Optional[str] = None
    approved_by: Optional[str] = None
    ticket_reference: Optional[str] = Field(default=None, max_length=128)


class ProvisionCreate(ProvisionBase):
    """Schema for creating a provision."""

    servers: List[int] = Field(description="List of server IDs")


class ProvisionUpdate(BaseModel):
    """Schema for updating a provision."""

    status: Optional[ProvisionStatus] = None
    grant_end: Optional[datetime] = None
    justification: Optional[str] = None


class ProvisionResponse(ProvisionBase):
    """Schema for provision response."""

    id: int
    server_id: int
    status: ProvisionStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProvisionWithServer(ProvisionResponse):
    """Provision with server information."""

    server_hostname: Optional[str] = None
    server_fqdn: Optional[str] = None


class JITAccessRequest(BaseModel):
    """Request for just-in-time access."""

    server_id: int
    principal_type: PrincipalType
    principal_name: str
    sudo_rule: str = Field(default="ALL=(ALL) ALL")
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    justification: str
    auto_expire: bool = Field(default=True)
    notify_on_use: bool = Field(default=False)


class JITAccessResponse(BaseModel):
    """Response for JIT access creation."""

    provision_id: int
    expires_at: datetime
    message: str


class BulkProvisionRequest(BaseModel):
    """Request for bulk provisioning."""

    provision_ids: List[int] = Field(description="List of provision IDs to deploy")
    thread_count: int = Field(default=50, ge=1, le=200)


class BulkProvisionResponse(BaseModel):
    """Response for bulk provisioning."""

    total: int
    completed: int
    failed: int
    deployment_job_id: Optional[str] = None


class RevokeProvisionRequest(BaseModel):
    """Request to revoke a provision."""

    reason: Optional[str] = None
