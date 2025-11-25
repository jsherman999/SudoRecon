"""Scan service for log collection and analysis."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import JobStatus, ScanJob, Server, SudoLog
from backend.schemas import ScanOptions
from backend.ssh.parsers.auth_log import AuthLogParser
from backend.ssh.pool import SSHPoolManager


class ScanService:
    """Service for scanning servers and collecting sudo logs."""

    def __init__(self, db: Session):
        """Initialize scan service.

        Args:
            db: Database session
        """
        self.db = db
        self.parser = AuthLogParser()

    async def scan_single_host(
        self,
        hostname: str,
        options: Optional[ScanOptions] = None,
        job_id: Optional[UUID] = None,
    ) -> Dict[str, any]:
        """Scan a single host for sudo logs.

        Args:
            hostname: Target hostname or FQDN
            options: Scan options
            job_id: Associated job ID

        Returns:
            Scan results
        """
        options = options or ScanOptions()

        # Get or create server entry
        server = self.db.execute(
            select(Server).where(Server.fqdn == hostname)
        ).scalar_one_or_none()

        if not server:
            server = Server(hostname=hostname.split(".")[0], fqdn=hostname)
            self.db.add(server)
            self.db.commit()
            self.db.refresh(server)

        # Create SSH pool
        ssh_pool = SSHPoolManager(max_concurrent=1, timeout=options.timeout_per_host)

        # Read log files from server
        all_entries = []
        for log_source in options.log_sources:
            # Try common log locations
            log_paths = [
                f"/var/log/{log_source}",
                f"/var/log/auth/{log_source}",
            ]

            for log_path in log_paths:
                result = await ssh_pool.read_file_from_host(hostname, log_path)
                if result["success"] and result["stdout"]:
                    # Parse the log content
                    entries = self.parser.parse_file(result["stdout"])
                    all_entries.extend(entries)
                    break  # Found the log file, no need to try other paths

        # Filter entries by time range if specified
        if options.time_range_start or options.time_range_end:
            filtered_entries = []
            for entry in all_entries:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if options.time_range_start and entry_time < options.time_range_start:
                    continue
                if options.time_range_end and entry_time > options.time_range_end:
                    continue
                filtered_entries.append(entry)
            all_entries = filtered_entries

        # Filter denied commands if requested
        if not options.include_denied:
            all_entries = [e for e in all_entries if e["result"] == "ACCEPT"]

        # Store logs in database
        stored_count = 0
        for entry in all_entries:
            log = SudoLog(
                server_id=server.id,
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                username=entry["username"],
                tty=entry.get("tty"),
                pwd=entry.get("pwd"),
                runas_user=entry.get("runas_user"),
                command=entry["command"],
                result=entry["result"],
                raw_log=entry["raw_log"],
            )
            self.db.add(log)
            stored_count += 1

        # Update server last scan time
        server.last_scan_at = datetime.utcnow()
        self.db.commit()

        return {
            "hostname": hostname,
            "server_id": server.id,
            "logs_found": len(all_entries),
            "logs_stored": stored_count,
            "success": True,
        }

    async def scan_multiple_hosts(
        self,
        hostnames: List[str],
        options: Optional[ScanOptions] = None,
        job_id: Optional[UUID] = None,
        thread_count: int = 50,
    ) -> Dict[str, any]:
        """Scan multiple hosts in parallel.

        Args:
            hostnames: List of target hostnames
            options: Scan options
            job_id: Associated job ID
            thread_count: Number of parallel threads

        Returns:
            Aggregated scan results
        """
        options = options or ScanOptions()

        # Update job status if provided
        if job_id:
            job = self.db.execute(select(ScanJob).where(ScanJob.id == job_id)).scalar_one_or_none()
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow()
                job.total_hosts = len(hostnames)
                self.db.commit()

        # Scan hosts in batches
        results = []
        completed = 0
        failed = 0

        for hostname in hostnames:
            try:
                result = await self.scan_single_host(hostname, options, job_id)
                results.append(result)
                if result["success"]:
                    completed += 1
                else:
                    failed += 1
            except Exception as e:
                results.append({
                    "hostname": hostname,
                    "success": False,
                    "error": str(e),
                })
                failed += 1

            # Update job progress
            if job_id and job:
                job.completed_hosts = completed
                job.failed_hosts = failed
                job.progress = int((completed + failed) / len(hostnames) * 100)
                self.db.commit()

        # Mark job as completed
        if job_id and job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            self.db.commit()

        return {
            "total_hosts": len(hostnames),
            "completed": completed,
            "failed": failed,
            "results": results,
        }
