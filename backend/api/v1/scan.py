"""Scan API endpoints."""

import asyncio
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models import JobStatus, ScanJob, ServerGroup, ServerGroupMember
from backend.schemas import (
    ScanFileRequest,
    ScanGroupRequest,
    ScanJobDetail,
    ScanJobResponse,
    ScanSingleRequest,
)
from backend.services.scan_service import ScanService

router = APIRouter()


async def run_scan_task(
    job_id: str,
    hostnames: list[str],
    options: dict,
    thread_count: int,
):
    """Background task to run scan."""
    from backend.db.session import SessionLocal

    db = SessionLocal()
    try:
        service = ScanService(db)
        await service.scan_multiple_hosts(
            hostnames=hostnames,
            options=None,  # TODO: Convert options dict to ScanOptions
            job_id=job_id,
            thread_count=thread_count,
        )
    finally:
        db.close()


@router.post("/single", response_model=ScanJobResponse)
async def scan_single_host(
    request: ScanSingleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Initiate a sudo log scan on a single server."""
    # Create scan job
    job = ScanJob(
        id=uuid4(),
        job_type="log_scan",
        target_type="single",
        target_spec=request.hostname,
        thread_count=1,
        status=JobStatus.PENDING,
        total_hosts=1,
        created_by=current_user,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Schedule background task
    background_tasks.add_task(
        run_scan_task,
        str(job.id),
        [request.hostname],
        request.options.model_dump() if request.options else {},
        1,
    )

    return ScanJobResponse(
        job_id=job.id,
        status=job.status,
        message="Scan job queued successfully",
        status_url=f"/api/v1/scan/jobs/{job.id}",
        stream_url=None,
    )


@router.post("/group", response_model=ScanJobResponse)
async def scan_group(
    request: ScanGroupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Scan all servers in a group with parallel execution."""
    # Get group and its servers
    group = (
        db.execute(select(ServerGroup).where(ServerGroup.id == request.group_id))
        .scalar_one_or_none()
    )
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {request.group_id} not found",
        )

    # Get all servers in group
    members = (
        db.execute(
            select(ServerGroupMember).where(ServerGroupMember.group_id == request.group_id)
        )
        .scalars()
        .all()
    )

    if not members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group {group.name} has no servers",
        )

    # Get server FQDNs
    from backend.models import Server

    hostnames = []
    for member in members:
        server = db.execute(select(Server).where(Server.id == member.server_id)).scalar_one()
        hostnames.append(server.fqdn)

    # Create scan job
    job = ScanJob(
        id=uuid4(),
        job_type="log_scan",
        target_type="group",
        target_spec=group.name,
        thread_count=request.thread_count,
        status=JobStatus.PENDING,
        total_hosts=len(hostnames),
        created_by=current_user,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Schedule background task
    background_tasks.add_task(
        run_scan_task,
        str(job.id),
        hostnames,
        request.options.model_dump() if request.options else {},
        request.thread_count,
    )

    return ScanJobResponse(
        job_id=job.id,
        status=job.status,
        message=f"Scan job queued for {len(hostnames)} servers",
        status_url=f"/api/v1/scan/jobs/{job.id}",
        stream_url=None,
    )


@router.post("/file", response_model=ScanJobResponse)
async def scan_from_file(
    request: ScanFileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Scan servers from an uploaded list."""
    if not request.hostnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hostnames provided",
        )

    # Create scan job
    job = ScanJob(
        id=uuid4(),
        job_type="log_scan",
        target_type="file",
        target_spec=f"{len(request.hostnames)} hosts",
        thread_count=request.thread_count,
        status=JobStatus.PENDING,
        total_hosts=len(request.hostnames),
        created_by=current_user,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Schedule background task
    background_tasks.add_task(
        run_scan_task,
        str(job.id),
        request.hostnames,
        request.options.model_dump() if request.options else {},
        request.thread_count,
    )

    return ScanJobResponse(
        job_id=job.id,
        status=job.status,
        message=f"Scan job queued for {len(request.hostnames)} servers",
        status_url=f"/api/v1/scan/jobs/{job.id}",
        stream_url=None,
    )


@router.get("/jobs", response_model=list[ScanJobDetail])
def list_scan_jobs(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """List all scan jobs."""
    jobs = db.execute(select(ScanJob).order_by(ScanJob.created_at.desc())).scalars().all()
    return [ScanJobDetail.model_validate(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ScanJobDetail)
def get_scan_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get scan job status and results."""
    job = db.execute(select(ScanJob).where(ScanJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    return ScanJobDetail.model_validate(job)


@router.delete("/jobs/{job_id}")
def cancel_scan_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Cancel a running scan job."""
    job = db.execute(select(ScanJob).where(ScanJob.id == job_id)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status}",
        )

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    db.commit()

    return {"message": "Job cancelled successfully"}
