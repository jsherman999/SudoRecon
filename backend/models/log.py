"""Sudo log models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SudoLog(Base):
    """Sudo log entry model."""

    __tablename__ = "sudo_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    tty: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pwd: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    runas_user: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)  # ACCEPT or DENY
    raw_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="sudo_logs")

    __table_args__ = (
        Index("idx_sudo_logs_server_timestamp", "server_id", "timestamp"),
        Index("idx_sudo_logs_username", "username"),
        Index(
            "idx_sudo_logs_command_gin",
            "command",
            postgresql_using="gin",
            postgresql_ops={"command": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SudoLog(id={self.id}, server_id={self.server_id}, "
            f"username={self.username}, result={self.result})>"
        )
