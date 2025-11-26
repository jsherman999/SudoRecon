"""Configuration management for SudoRecon application."""

from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SudoRecon"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://sudorecon:secret@localhost:5432/sudorecon"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_workers: int = 4
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Security
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    api_key_hash_algorithm: str = "sha256"

    # SSH
    ssh_user: str = "sudorecon"
    ssh_key_path: str = "/home/sudorecon/.ssh/id_rsa"
    ssh_control_path: str = "/var/run/sudorecon/ssh-%r@%h:%p"
    ssh_control_persist: int = 600
    ssh_connect_timeout: int = 10
    ssh_max_connections: int = 200
    ssh_per_host_limit: int = 3

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")
    celery_task_time_limit: int = 3600

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
