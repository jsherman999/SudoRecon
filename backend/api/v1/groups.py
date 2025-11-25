"""Server group management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models import Server, ServerGroup, ServerGroupMember
from backend.schemas import (
    AddGroupMembersRequest,
    MessageResponse,
    ServerGroupCreate,
    ServerGroupResponse,
    ServerGroupUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ServerGroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List all server groups."""
    groups = db.execute(select(ServerGroup).order_by(ServerGroup.name)).scalars().all()
    return [ServerGroupResponse.model_validate(group) for group in groups]


@router.post("", response_model=ServerGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_data: ServerGroupCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create a new server group."""
    # Check if group already exists
    existing = (
        db.execute(select(ServerGroup).where(ServerGroup.name == group_data.name))
        .scalar_one_or_none()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Group with name {group_data.name} already exists",
        )

    # Create group
    group = ServerGroup(**group_data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)

    return ServerGroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=ServerGroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get group by ID."""
    group = (
        db.execute(select(ServerGroup).where(ServerGroup.id == group_id)).scalar_one_or_none()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found",
        )

    return ServerGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=ServerGroupResponse)
def update_group(
    group_id: int,
    group_data: ServerGroupUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Update group information."""
    group = (
        db.execute(select(ServerGroup).where(ServerGroup.id == group_id)).scalar_one_or_none()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found",
        )

    # Update fields
    for field, value in group_data.model_dump(exclude_unset=True).items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)

    return ServerGroupResponse.model_validate(group)


@router.delete("/{group_id}", response_model=MessageResponse)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Delete a server group."""
    group = (
        db.execute(select(ServerGroup).where(ServerGroup.id == group_id)).scalar_one_or_none()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found",
        )

    db.delete(group)
    db.commit()

    return MessageResponse(message=f"Group {group.name} deleted successfully")


@router.post("/{group_id}/members", response_model=MessageResponse)
def add_group_members(
    group_id: int,
    request: AddGroupMembersRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Add servers to a group."""
    # Check if group exists
    group = (
        db.execute(select(ServerGroup).where(ServerGroup.id == group_id)).scalar_one_or_none()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found",
        )

    # Add each server to the group
    added_count = 0
    for server_id in request.server_ids:
        # Check if server exists
        server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
        if not server:
            continue

        # Check if already a member
        existing = (
            db.execute(
                select(ServerGroupMember).where(
                    ServerGroupMember.server_id == server_id,
                    ServerGroupMember.group_id == group_id,
                )
            )
            .scalar_one_or_none()
        )
        if existing:
            continue

        # Add membership
        membership = ServerGroupMember(server_id=server_id, group_id=group_id)
        db.add(membership)
        added_count += 1

    db.commit()

    return MessageResponse(message=f"Added {added_count} servers to group {group.name}")


@router.delete("/{group_id}/members/{server_id}", response_model=MessageResponse)
def remove_group_member(
    group_id: int,
    server_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Remove a server from a group."""
    membership = (
        db.execute(
            select(ServerGroupMember).where(
                ServerGroupMember.server_id == server_id,
                ServerGroupMember.group_id == group_id,
            )
        )
        .scalar_one_or_none()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server {server_id} is not a member of group {group_id}",
        )

    db.delete(membership)
    db.commit()

    return MessageResponse(message="Server removed from group successfully")
