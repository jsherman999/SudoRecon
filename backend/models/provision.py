"""Sudo provision models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class PrincipalType(str, enum.Enum):
    """Type of principal (user or group)."""

    USER = "user"
    GROUP = "group"


class ProvisionStatus(str, enum.Enum):
    """Provision status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class SudoProvision(Base, TimestampMixin):
    """Sudo provision model representing a sudo grant."""

    __tablename__ = "sudo_provisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    principal_type: Mapped[PrincipalType] = mapped_column(
        Enum(PrincipalType), nullable=False
    )
    principal_name: Mapped[str] = mapped_column(String(512), nullable=False)
    sudo_rule: Mapped[str] = mapped_column(Text, nullable=False)
    is_jit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    grant_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grant_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ProvisionStatus] = mapped_column(
        Enum(ProvisionStatus), default=ProvisionStatus.PENDING, nullable=False
    )
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ticket_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="provisions")
    history: Mapped[list["ProvisionHistory"]] = relationship(
        "ProvisionHistory", back_populates="provision", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_provisions_status", "status"),
        Index(
            "idx_provisions_grant_end",
            "grant_end",
            postgresql_where=Text("status = 'active'"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SudoProvision(id={self.id}, principal={self.principal_name}, "
            f"status={self.status})>"
        )


class ProvisionHistory(Base):
    """Provision history tracking model."""

    __tablename__ = "provision_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    provision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sudo_provisions.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    provision: Mapped[Optional["SudoProvision"]] = relationship(
        "SudoProvision", back_populates="history"
    )

    def __repr__(self) -> str:
        return f"<ProvisionHistory(id={self.id}, action={self.action})>"
