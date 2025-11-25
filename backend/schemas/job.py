"""Job-related Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.job import JobStatus


class ScanOptions(BaseModel):
    """Options for scan jobs."""

    log_sources: List[str] = Field(
        default=["auth.log", "secure", "sudo.log"], description="Log files to scan"
    )
    time_range_start: Optional[datetime] = Field(default=None, description="Start time")
    time_range_end: Optional[datetime] = Field(default=None, description="End time")
    include_denied: bool = Field(default=True, description="Include denied commands")
    timeout_per_host: int = Field(default=30, ge=5, le=300, description="Timeout per host")
    continue_on_error: bool = Field(default=True, description="Continue if errors occur")


class ScanSingleRequest(BaseModel):
    """Request to scan a single server."""

    hostname: str = Field(description="Hostname or FQDN to scan")
    options: Optional[ScanOptions] = Field(default_factory=ScanOptions)


class ScanGroupRequest(BaseModel):
    """Request to scan a server group."""

    group_id: int = Field(description="Server group ID")
    thread_count: int = Field(default=50, ge=1, le=200, description="Number of parallel threads")
    options: Optional[ScanOptions] = Field(default_factory=ScanOptions)


class ScanFileRequest(BaseModel):
    """Request to scan servers from a file."""

    hostnames: List[str] = Field(description="List of hostnames to scan")
    thread_count: int = Field(default=100, ge=1, le=200)
    options: Optional[ScanOptions] = Field(default_factory=ScanOptions)


class ScanJobResponse(BaseModel):
    """Response for scan job creation."""

    job_id: UUID = Field(description="Job ID")
    status: JobStatus = Field(description="Job status")
    message: str = Field(description="Status message")
    status_url: str = Field(description="URL to check job status")
    stream_url: Optional[str] = Field(default=None, description="SSE stream URL")


class ScanJobDetail(BaseModel):
    """Detailed scan job information."""

    id: UUID
    job_type: str
    target_type: str
    target_spec: str
    thread_count: int
    status: JobStatus
    progress: int
    total_hosts: int
    completed_hosts: int
    failed_hosts: int
    error_details: List[Dict] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
