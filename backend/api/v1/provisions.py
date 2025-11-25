"""Provision management API endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models import ProvisionStatus, Server, SudoProvision
from backend.schemas import (
    BulkProvisionRequest,
    BulkProvisionResponse,
    JITAccessRequest,
    JITAccessResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    ProvisionCreate,
    ProvisionResponse,
    ProvisionUpdate,
    ProvisionWithServer,
    RevokeProvisionRequest,
)
from backend.services.provision_service import ProvisionService

router = APIRouter()


async def deploy_provision_task(provision_id: int, server_fqdn: str):
    """Background task to deploy a provision."""
    from backend.db.session import SessionLocal

    db = SessionLocal()
    try:
        service = ProvisionService(db)
        await service.deploy_provision(provision_id, server_fqdn)
    finally:
        db.close()


@router.get("", response_model=PaginatedResponse[ProvisionWithServer])
def list_provisions(
    status: Optional[ProvisionStatus] = Query(default=None),
    server_id: Optional[int] = Query(default=None),
    principal_name: Optional[str] = Query(default=None),
    is_jit: Optional[bool] = Query(default=None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List all provisions with filters."""
    # Build query with join to server
    query = select(SudoProvision, Server).join(Server, SudoProvision.server_id == Server.id)

    # Apply filters
    if status:
        query = query.where(SudoProvision.status == status)
    if server_id:
        query = query.where(SudoProvision.server_id == server_id)
    if principal_name:
        query = query.where(SudoProvision.principal_name.ilike(f"%{principal_name}%"))
    if is_jit is not None:
        query = query.where(SudoProvision.is_jit == is_jit)

    # Count total
    from sqlalchemy import func
    count_query = select(func.count()).select_from(SudoProvision)
    if status:
        count_query = count_query.where(SudoProvision.status == status)
    if server_id:
        count_query = count_query.where(SudoProvision.server_id == server_id)
    if principal_name:
        count_query = count_query.where(SudoProvision.principal_name.ilike(f"%{principal_name}%"))
    if is_jit is not None:
        count_query = count_query.where(SudoProvision.is_jit == is_jit)

    total = db.execute(count_query).scalar_one()

    # Apply sorting
    query = query.order_by(SudoProvision.created_at.desc())

    # Apply pagination
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)

    # Execute
    results = db.execute(query).all()

    # Build response
    provisions = []
    for provision, server in results:
        prov_dict = {
            "id": provision.id,
            "server_id": provision.server_id,
            "principal_type": provision.principal_type,
            "principal_name": provision.principal_name,
            "sudo_rule": provision.sudo_rule,
            "is_jit": provision.is_jit,
            "grant_start": provision.grant_start,
            "grant_end": provision.grant_end,
            "status": provision.status,
            "justification": provision.justification,
            "approved_by": provision.approved_by,
            "ticket_reference": provision.ticket_reference,
            "created_at": provision.created_at,
            "updated_at": provision.updated_at,
            "server_hostname": server.hostname,
            "server_fqdn": server.fqdn,
        }
        provisions.append(ProvisionWithServer(**prov_dict))

    pages = (total + pagination.page_size - 1) // pagination.page_size

    return PaginatedResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
        results=provisions,
    )


@router.post("", response_model=list[ProvisionResponse], status_code=status.HTTP_201_CREATED)
def create_provisions(
    request: ProvisionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create new sudo provisions."""
    service = ProvisionService(db)
    provisions = []

    for server_id in request.servers:
        # Verify server exists
        server = db.execute(select(Server).where(Server.id == server_id)).scalar_one_or_none()
        if not server:
            continue

        # Create provision
        provision = service.create_provision(
            server_id=server_id,
            principal_type=request.principal_type,
            principal_name=request.principal_name,
            sudo_rule=request.sudo_rule,
            is_jit=request.is_jit,
            grant_start=request.grant_start,
            grant_end=request.grant_end,
            justification=request.justification,
            approved_by=current_user,
            ticket_reference=request.ticket_reference,
        )
        provisions.append(provision)

        # Schedule deployment
        background_tasks.add_task(deploy_provision_task, provision.id, server.fqdn)

    return [ProvisionResponse.model_validate(p) for p in provisions]


@router.get("/{provision_id}", response_model=ProvisionResponse)
def get_provision(
    provision_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get provision details."""
    provision = db.execute(
        select(SudoProvision).where(SudoProvision.id == provision_id)
    ).scalar_one_or_none()

    if not provision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provision with ID {provision_id} not found",
        )

    return ProvisionResponse.model_validate(provision)


@router.put("/{provision_id}", response_model=ProvisionResponse)
def update_provision(
    provision_id: int,
    update_data: ProvisionUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Update a provision."""
    provision = db.execute(
        select(SudoProvision).where(SudoProvision.id == provision_id)
    ).scalar_one_or_none()

    if not provision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provision with ID {provision_id} not found",
        )

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(provision, field, value)

    db.commit()
    db.refresh(provision)

    return ProvisionResponse.model_validate(provision)


@router.delete("/{provision_id}", response_model=MessageResponse)
async def revoke_provision(
    provision_id: int,
    revoke_data: Optional[RevokeProvisionRequest] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Revoke a provision."""
    provision = db.execute(
        select(SudoProvision).where(SudoProvision.id == provision_id)
    ).scalar_one_or_none()

    if not provision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provision with ID {provision_id} not found",
        )

    # Get server
    server = db.execute(
        select(Server).where(Server.id == provision.server_id)
    ).scalar_one()

    # Revoke via service
    service = ProvisionService(db)
    result = await service.revoke_provision(provision_id, server.fqdn, current_user)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )

    return MessageResponse(message="Provision revoked successfully")


@router.post("/jit", response_model=JITAccessResponse, status_code=status.HTTP_201_CREATED)
def create_jit_access(
    request: JITAccessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create just-in-time sudo access."""
    # Verify server exists
    server = db.execute(
        select(Server).where(Server.id == request.server_id)
    ).scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with ID {request.server_id} not found",
        )

    # Create JIT provision
    service = ProvisionService(db)
    provision = service.create_provision(
        server_id=request.server_id,
        principal_type=request.principal_type,
        principal_name=request.principal_name,
        sudo_rule=request.sudo_rule,
        is_jit=True,
        duration_minutes=request.duration_minutes,
        justification=request.justification,
        approved_by=current_user,
    )

    # Schedule deployment
    background_tasks.add_task(deploy_provision_task, provision.id, server.fqdn)

    return JITAccessResponse(
        provision_id=provision.id,
        expires_at=provision.grant_end,
        message=f"JIT access granted for {request.duration_minutes} minutes",
    )


@router.post("/bulk", response_model=BulkProvisionResponse)
async def bulk_provision(
    request: BulkProvisionRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Deploy multiple provisions in parallel."""
    service = ProvisionService(db)
    result = await service.deploy_bulk_provisions(
        request.provision_ids,
        request.thread_count,
    )

    return BulkProvisionResponse(
        total=result["total"],
        completed=result["completed"],
        failed=result["failed"],
    )


@router.get("/expiring", response_model=list[ProvisionWithServer])
def get_expiring_provisions(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get provisions expiring soon."""
    threshold = datetime.utcnow() + timedelta(hours=hours)

    results = db.execute(
        select(SudoProvision, Server)
        .join(Server, SudoProvision.server_id == Server.id)
        .where(
            SudoProvision.status == ProvisionStatus.ACTIVE,
            SudoProvision.grant_end <= threshold,
            SudoProvision.grant_end > datetime.utcnow(),
        )
        .order_by(SudoProvision.grant_end.asc())
    ).all()

    provisions = []
    for provision, server in results:
        prov_dict = {
            "id": provision.id,
            "server_id": provision.server_id,
            "principal_type": provision.principal_type,
            "principal_name": provision.principal_name,
            "sudo_rule": provision.sudo_rule,
            "is_jit": provision.is_jit,
            "grant_start": provision.grant_start,
            "grant_end": provision.grant_end,
            "status": provision.status,
            "justification": provision.justification,
            "approved_by": provision.approved_by,
            "ticket_reference": provision.ticket_reference,
            "created_at": provision.created_at,
            "updated_at": provision.updated_at,
            "server_hostname": server.hostname,
            "server_fqdn": server.fqdn,
        }
        provisions.append(ProvisionWithServer(**prov_dict))

    return provisions
