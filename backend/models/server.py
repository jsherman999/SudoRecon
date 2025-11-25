"""Server and server group models."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ServerStatus(str, enum.Enum):
    """Server status enumeration."""

    ACTIVE = "active"
    UNREACHABLE = "unreachable"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Server(Base, TimestampMixin):
    """Server model representing a managed host."""

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    fqdn: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus), default=ServerStatus.ACTIVE, nullable=False
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    sudo_logs: Mapped[List["SudoLog"]] = relationship(
        "SudoLog", back_populates="server", cascade="all, delete-orphan"
    )
    provisions: Mapped[List["SudoProvision"]] = relationship(
        "SudoProvision", back_populates="server", cascade="all, delete-orphan"
    )
    group_memberships: Mapped[List["ServerGroupMember"]] = relationship(
        "ServerGroupMember", back_populates="server", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_servers_fqdn", "fqdn"),)

    def __repr__(self) -> str:
        return f"<Server(id={self.id}, fqdn={self.fqdn}, status={self.status})>"


class ServerGroup(Base, TimestampMixin):
    """Server group for organizing hosts."""

    __tablename__ = "server_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    members: Mapped[List["ServerGroupMember"]] = relationship(
        "ServerGroupMember", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ServerGroup(id={self.id}, name={self.name})>"


class ServerGroupMember(Base):
    """Association table for server group membership."""

    __tablename__ = "server_group_members"

    server_id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(primary_key=True)

    # Relationships with foreign keys
    server: Mapped["Server"] = relationship(
        "Server", back_populates="group_memberships", foreign_keys=[server_id]
    )
    group: Mapped["ServerGroup"] = relationship(
        "ServerGroup", back_populates="members", foreign_keys=[group_id]
    )

    def __repr__(self) -> str:
        return f"<ServerGroupMember(server_id={self.server_id}, group_id={self.group_id})>"
