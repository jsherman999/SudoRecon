"""Log search and analysis API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models import Server, SudoLog
from backend.schemas import (
    LogSearchParams,
    LogStats,
    PaginatedResponse,
    PaginationParams,
    SudoLogWithServer,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SudoLogWithServer])
def search_logs(
    q: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    hostname: Optional[str] = Query(default=None),
    server_id: Optional[int] = Query(default=None),
    result: Optional[str] = Query(default=None),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Search sudo logs with filters."""
    # Build query with join to server
    query = select(SudoLog, Server).join(Server, SudoLog.server_id == Server.id)

    # Apply filters
    if q:
        # Full-text search on command
        query = query.where(SudoLog.command.ilike(f"%{q}%"))

    if username:
        query = query.where(SudoLog.username == username)

    if hostname:
        query = query.where(
            or_(
                Server.hostname.ilike(f"%{hostname}%"),
                Server.fqdn.ilike(f"%{hostname}%"),
            )
        )

    if server_id:
        query = query.where(SudoLog.server_id == server_id)

    if result:
        query = query.where(SudoLog.result == result.upper())

    if start_time:
        query = query.where(SudoLog.timestamp >= start_time)

    if end_time:
        query = query.where(SudoLog.timestamp <= end_time)

    # Get total count
    count_query = select(func.count()).select_from(SudoLog)
    # Apply same filters to count query
    if q:
        count_query = count_query.where(SudoLog.command.ilike(f"%{q}%"))
    if username:
        count_query = count_query.where(SudoLog.username == username)
    if server_id:
        count_query = count_query.where(SudoLog.server_id == server_id)
    if result:
        count_query = count_query.where(SudoLog.result == result.upper())
    if start_time:
        count_query = count_query.where(SudoLog.timestamp >= start_time)
    if end_time:
        count_query = count_query.where(SudoLog.timestamp <= end_time)

    total = db.execute(count_query).scalar_one()

    # Apply sorting
    if pagination.sort:
        order_column = getattr(SudoLog, pagination.sort, SudoLog.timestamp)
        if pagination.order == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    else:
        query = query.order_by(SudoLog.timestamp.desc())

    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)

    # Execute query
    results = db.execute(query).all()

    # Build response objects
    log_responses = []
    for log, server in results:
        log_dict = {
            "id": log.id,
            "server_id": log.server_id,
            "timestamp": log.timestamp,
            "username": log.username,
            "tty": log.tty,
            "pwd": log.pwd,
            "runas_user": log.runas_user,
            "command": log.command,
            "result": log.result,
            "raw_log": log.raw_log,
            "session_id": log.session_id,
            "created_at": log.created_at,
            "server_hostname": server.hostname,
            "server_fqdn": server.fqdn,
        }
        log_responses.append(SudoLogWithServer(**log_dict))

    # Calculate total pages
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
        results=log_responses,
    )


@router.get("/stats", response_model=LogStats)
def get_log_statistics(
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    server_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get aggregated log statistics."""
    # Build base query
    query = select(SudoLog)

    if start_time:
        query = query.where(SudoLog.timestamp >= start_time)
    if end_time:
        query = query.where(SudoLog.timestamp <= end_time)
    if server_id:
        query = query.where(SudoLog.server_id == server_id)

    # Get total count
    total_logs = db.execute(
        select(func.count()).select_from(query.subquery())
    ).scalar_one()

    # Get accept/deny counts
    accept_count = db.execute(
        select(func.count())
        .select_from(query.where(SudoLog.result == "ACCEPT").subquery())
    ).scalar_one()

    deny_count = db.execute(
        select(func.count())
        .select_from(query.where(SudoLog.result == "DENY").subquery())
    ).scalar_one()

    # Get unique users
    unique_users = db.execute(
        select(func.count(func.distinct(SudoLog.username)))
        .select_from(query.subquery())
    ).scalar_one()

    # Get unique servers
    unique_servers = db.execute(
        select(func.count(func.distinct(SudoLog.server_id)))
        .select_from(query.subquery())
    ).scalar_one()

    # Get time range
    time_range_query = select(
        func.min(SudoLog.timestamp),
        func.max(SudoLog.timestamp),
    )
    if start_time:
        time_range_query = time_range_query.where(SudoLog.timestamp >= start_time)
    if end_time:
        time_range_query = time_range_query.where(SudoLog.timestamp <= end_time)
    if server_id:
        time_range_query = time_range_query.where(SudoLog.server_id == server_id)

    time_range_start, time_range_end = db.execute(time_range_query).first()

    return LogStats(
        total_logs=total_logs,
        accept_count=accept_count,
        deny_count=deny_count,
        unique_users=unique_users,
        unique_servers=unique_servers,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
    )


@router.get("/users/{username}")
def get_logs_by_user(
    username: str,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get all logs for a specific user."""
    return search_logs(
        username=username,
        pagination=pagination,
        db=db,
        current_user=current_user,
    )
