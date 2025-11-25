"""Maintenance tasks for Celery."""

import asyncio
from datetime import datetime, timedelta

from backend.db.session import SessionLocal
from backend.models import JobStatus, ScanJob
from backend.services.provision_service import ProvisionService
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.maintenance_tasks.check_expired_provisions")
def check_expired_provisions():
    """Check for and mark expired provisions."""
    db = SessionLocal()
    try:
        service = ProvisionService(db)
        expired = service.check_expired_provisions()

        # Revoke expired provisions
        for provision in expired:
            from backend.models import Server
            from sqlalchemy import select

            server = db.execute(
                select(Server).where(Server.id == provision.server_id)
            ).scalar_one()

            # Schedule revocation
            asyncio.run(service.revoke_provision(provision.id, server.fqdn, "system"))

        return {
            "expired_count": len(expired),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@celery_app.task(name="backend.tasks.maintenance_tasks.cleanup_old_jobs")
def cleanup_old_jobs(days: int = 30):
    """Clean up old completed scan jobs.

    Args:
        days: Number of days to keep jobs
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Find old completed/failed jobs
        from sqlalchemy import select

        old_jobs = db.execute(
            select(ScanJob).where(
                ScanJob.completed_at < cutoff_date,
                ScanJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
            )
        ).scalars().all()

        count = len(old_jobs)

        # Delete jobs
        for job in old_jobs:
            db.delete(job)

        db.commit()

        return {
            "deleted_count": count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()


@celery_app.task(name="backend.tasks.maintenance_tasks.auto_revoke_expired")
def auto_revoke_expired():
    """Automatically revoke expired JIT provisions.

    This task runs periodically to ensure expired JIT grants are removed.
    """
    db = SessionLocal()
    try:
        service = ProvisionService(db)
        expired = service.check_expired_provisions()

        revoked_count = 0
        for provision in expired:
            if provision.is_jit:  # Only auto-revoke JIT grants
                from backend.models import Server
                from sqlalchemy import select

                server = db.execute(
                    select(Server).where(Server.id == provision.server_id)
                ).scalar_one()

                try:
                    asyncio.run(service.revoke_provision(provision.id, server.fqdn, "auto-expire"))
                    revoked_count += 1
                except Exception as e:
                    print(f"Failed to revoke provision {provision.id}: {e}")

        return {
            "expired_count": len(expired),
            "revoked_count": revoked_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db.close()
