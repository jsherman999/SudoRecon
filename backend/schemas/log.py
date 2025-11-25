"""Log-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SudoLogBase(BaseModel):
    """Base sudo log schema."""

    timestamp: datetime
    username: str = Field(max_length=255)
    tty: Optional[str] = Field(default=None, max_length=64)
    pwd: Optional[str] = Field(default=None, max_length=1024)
    runas_user: Optional[str] = Field(default=None, max_length=255)
    command: str
    result: str = Field(max_length=16, description="ACCEPT or DENY")
    raw_log: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None, max_length=64)


class SudoLogCreate(SudoLogBase):
    """Schema for creating a sudo log."""

    server_id: int


class SudoLogResponse(SudoLogBase):
    """Schema for sudo log response."""

    id: int
    server_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SudoLogWithServer(SudoLogResponse):
    """Sudo log with server information."""

    server_hostname: Optional[str] = None
    server_fqdn: Optional[str] = None


class LogSearchParams(BaseModel):
    """Parameters for searching logs."""

    q: Optional[str] = Field(default=None, description="Full-text search query")
    username: Optional[str] = Field(default=None, description="Filter by username")
    hostname: Optional[str] = Field(default=None, description="Filter by hostname")
    server_id: Optional[int] = Field(default=None, description="Filter by server ID")
    result: Optional[str] = Field(default=None, description="ACCEPT or DENY")
    start_time: Optional[datetime] = Field(default=None, description="Start of time range")
    end_time: Optional[datetime] = Field(default=None, description="End of time range")


class LogStats(BaseModel):
    """Log statistics."""

    total_logs: int
    accept_count: int
    deny_count: int
    unique_users: int
    unique_servers: int
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
