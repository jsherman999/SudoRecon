"""Job models for background tasks."""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanJob(Base):
    """Scan job model for tracking background scanning operations."""

    __tablename__ = "scan_jobs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_spec: Mapped[str] = mapped_column(Text, nullable=False)
    thread_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_hosts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_hosts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_hosts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("idx_scan_jobs_status", "status"),)

    def __repr__(self) -> str:
        return f"<ScanJob(id={self.id}, job_type={self.job_type}, status={self.status})>"
