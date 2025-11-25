"""Server management API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models import Server
from backend.schemas import (
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    ServerCreate,
    ServerResponse,
    ServerUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ServerResponse])
def list_servers(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List all servers with pagination."""
    # Build query
    query = select(Server)

    # Apply sorting
    if pagination.sort:
        order_column = getattr(Server, pagination.sort, Server.created_at)
        if pagination.order == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    else:
        query = query.order_by(Server.created_at.desc())

    # Get total count
    total_query = select(func.count()).select_from(Server)
    total = db.execute(total_query).scalar_one()

    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)

    # Execute query
    result = db.execute(query).scalars().all()

    # Calculate total pages
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
        results=[ServerResponse.model_validate(server) for server in result],
    )


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(
    server_data: ServerCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create a new server."""
    # Check if server already exists
    existing = db.execute(select(Server).where(Server.fqdn == server_data.fqdn)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Server with FQDN {server_data.fqdn} already exists",
        )

    # Create server
    server = Server(**server_data.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)

    return ServerResponse.model_validate(server)


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get server by ID."""
    server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with ID {server_id} not found",
        )

    return ServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: int,
    server_data: ServerUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Update server information."""
    server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with ID {server_id} not found",
        )

    # Update fields
    for field, value in server_data.model_dump(exclude_unset=True).items():
        setattr(server, field, value)

    db.commit()
    db.refresh(server)

    return ServerResponse.model_validate(server)


@router.delete("/{server_id}", response_model=MessageResponse)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Delete a server."""
    server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with ID {server_id} not found",
        )

    db.delete(server)
    db.commit()

    return MessageResponse(message=f"Server {server.fqdn} deleted successfully")
