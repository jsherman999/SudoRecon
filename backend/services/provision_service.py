"""Provision service for sudo access management."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    JobStatus,
    PrincipalType,
    ProvisionHistory,
    ProvisionStatus,
    ScanJob,
    Server,
    SudoProvision,
)
from backend.ssh.pool import SSHPoolManager
from backend.utils.sudoers import SudoersManager


class ProvisionService:
    """Service for managing sudo provisions."""

    def __init__(self, db: Session):
        """Initialize provision service.

        Args:
            db: Database session
        """
        self.db = db
        self.sudoers_manager = SudoersManager()

    async def deploy_provision(
        self, provision_id: int, server_hostname: str
    ) -> Dict[str, any]:
        """Deploy a provision to a server.

        Args:
            provision_id: Provision ID
            server_hostname: Target server hostname

        Returns:
            Deployment result
        """
        # Get provision
        provision = self.db.execute(
            select(SudoProvision).where(SudoProvision.id == provision_id)
        ).scalar_one_or_none()

        if not provision:
            return {"success": False, "error": "Provision not found"}

        # Generate sudoers rule
        rule = self.sudoers_manager.generate_rule(
            provision_id=provision.id,
            principal_type=provision.principal_type,
            principal_name=provision.principal_name,
            sudo_rule=provision.sudo_rule,
            expires=provision.grant_end,
        )

        # Create SSH pool
        ssh_pool = SSHPoolManager(max_concurrent=1, timeout=30)

        # Create temporary file with rule
        temp_file = f"/tmp/sudoguard_provision_{provision_id}.tmp"
        create_file_cmd = f"cat > {temp_file} << 'SUDOGUARD_EOF'\n{rule}\nSUDOGUARD_EOF"

        result = await ssh_pool.execute_on_host(server_hostname, create_file_cmd)
        if not result["success"]:
            return {
                "success": False,
                "error": f"Failed to create temp file: {result['error']}",
            }

        # Validate syntax
        validate_cmd = f"sudo visudo -c -f {temp_file}"
        result = await ssh_pool.execute_on_host(server_hostname, validate_cmd)
        if not result["success"] or result["exit_code"] != 0:
            # Clean up temp file
            await ssh_pool.execute_on_host(server_hostname, f"rm -f {temp_file}")
            return {
                "success": False,
                "error": f"Invalid sudoers syntax: {result['stderr']}",
            }

        # Append to sudoers file
        sudoers_path = "/etc/sudoers.d/sudoguard"
        append_cmd = f"sudo bash -c 'cat {temp_file} >> {sudoers_path} && chmod 0440 {sudoers_path}'"
        result = await ssh_pool.execute_on_host(server_hostname, append_cmd)

        # Clean up temp file
        await ssh_pool.execute_on_host(server_hostname, f"rm -f {temp_file}")

        if not result["success"]:
            return {"success": False, "error": f"Failed to deploy: {result['error']}"}

        # Update provision status
        provision.status = ProvisionStatus.ACTIVE
        self.db.commit()

        # Create history entry
        history = ProvisionHistory(
            provision_id=provision.id,
            action="deployed",
            performed_by="system",
            details={"server": server_hostname, "timestamp": datetime.utcnow().isoformat()},
        )
        self.db.add(history)
        self.db.commit()

        return {
            "success": True,
            "provision_id": provision.id,
            "server": server_hostname,
        }

    async def revoke_provision(
        self, provision_id: int, server_hostname: str, performed_by: str = "system"
    ) -> Dict[str, any]:
        """Revoke a provision from a server.

        Args:
            provision_id: Provision ID
            server_hostname: Target server hostname
            performed_by: Who performed the revocation

        Returns:
            Revocation result
        """
        # Get provision
        provision = self.db.execute(
            select(SudoProvision).where(SudoProvision.id == provision_id)
        ).scalar_one_or_none()

        if not provision:
            return {"success": False, "error": "Provision not found"}

        # Create removal script
        remove_script = f"""
        sudo python3 - << 'PYTHON_EOF'
import re
import sys

sudoers_path = "/etc/sudoers.d/sudoguard"
provision_id = {provision_id}

try:
    with open(sudoers_path, "r") as f:
        lines = f.readlines()

    # Find and remove the provision block
    new_lines = []
    skip = False
    for line in lines:
        if f"# SUDOGUARD_PROVISION_ID={{provision_id}}" in line:
            skip = True
        elif skip and (line.startswith("# SUDOGUARD_PROVISION_ID=") or line.strip() == ""):
            skip = False
            if line.strip() == "":
                continue

        if not skip:
            new_lines.append(line)

    # Write back
    with open(sudoers_path, "w") as f:
        f.writelines(new_lines)

    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
        """

        # Execute removal
        ssh_pool = SSHPoolManager(max_concurrent=1, timeout=30)
        result = await ssh_pool.execute_on_host(server_hostname, remove_script)

        if not result["success"] or "SUCCESS" not in result["stdout"]:
            return {"success": False, "error": f"Failed to revoke: {result.get('stderr', 'Unknown error')}"}

        # Update provision status
        provision.status = ProvisionStatus.REVOKED
        self.db.commit()

        # Create history entry
        history = ProvisionHistory(
            provision_id=provision.id,
            action="revoked",
            performed_by=performed_by,
            details={"server": server_hostname, "timestamp": datetime.utcnow().isoformat()},
        )
        self.db.add(history)
        self.db.commit()

        return {
            "success": True,
            "provision_id": provision.id,
            "server": server_hostname,
        }

    def create_provision(
        self,
        server_id: int,
        principal_type: PrincipalType,
        principal_name: str,
        sudo_rule: str,
        is_jit: bool = False,
        duration_minutes: Optional[int] = None,
        grant_start: Optional[datetime] = None,
        grant_end: Optional[datetime] = None,
        justification: Optional[str] = None,
        approved_by: Optional[str] = None,
        ticket_reference: Optional[str] = None,
    ) -> SudoProvision:
        """Create a new provision.

        Args:
            server_id: Target server ID
            principal_type: USER or GROUP
            principal_name: Principal name
            sudo_rule: Sudo rule specification
            is_jit: Is this JIT access
            duration_minutes: Duration for JIT access
            grant_start: Start time (defaults to now)
            grant_end: End time (required for JIT)
            justification: Justification text
            approved_by: Approver username
            ticket_reference: Ticket reference

        Returns:
            Created provision
        """
        # Calculate times
        if grant_start is None:
            grant_start = datetime.utcnow()

        if is_jit and duration_minutes:
            grant_end = grant_start + timedelta(minutes=duration_minutes)

        # Create provision
        provision = SudoProvision(
            server_id=server_id,
            principal_type=principal_type,
            principal_name=principal_name,
            sudo_rule=sudo_rule,
            is_jit=is_jit,
            grant_start=grant_start,
            grant_end=grant_end,
            status=ProvisionStatus.PENDING,
            justification=justification,
            approved_by=approved_by,
            ticket_reference=ticket_reference,
        )

        self.db.add(provision)
        self.db.commit()
        self.db.refresh(provision)

        # Create history entry
        history = ProvisionHistory(
            provision_id=provision.id,
            action="created",
            performed_by=approved_by or "system",
            details={
                "principal": principal_name,
                "is_jit": is_jit,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        self.db.add(history)
        self.db.commit()

        return provision

    def check_expired_provisions(self) -> List[SudoProvision]:
        """Check for expired provisions.

        Returns:
            List of expired provisions
        """
        now = datetime.utcnow()
        expired = self.db.execute(
            select(SudoProvision).where(
                SudoProvision.status == ProvisionStatus.ACTIVE,
                SudoProvision.grant_end <= now,
            )
        ).scalars().all()

        # Mark as expired
        for provision in expired:
            provision.status = ProvisionStatus.EXPIRED

            # Create history entry
            history = ProvisionHistory(
                provision_id=provision.id,
                action="expired",
                performed_by="system",
                details={"expired_at": now.isoformat()},
            )
            self.db.add(history)

        self.db.commit()

        return list(expired)

    async def deploy_bulk_provisions(
        self,
        provision_ids: List[int],
        thread_count: int = 50,
    ) -> Dict[str, any]:
        """Deploy multiple provisions in parallel.

        Args:
            provision_ids: List of provision IDs
            thread_count: Number of parallel threads

        Returns:
            Deployment results
        """
        results = []
        completed = 0
        failed = 0

        for provision_id in provision_ids:
            # Get provision and server
            provision = self.db.execute(
                select(SudoProvision).where(SudoProvision.id == provision_id)
            ).scalar_one_or_none()

            if not provision:
                results.append({
                    "provision_id": provision_id,
                    "success": False,
                    "error": "Provision not found",
                })
                failed += 1
                continue

            server = self.db.execute(
                select(Server).where(Server.id == provision.server_id)
            ).scalar_one()

            # Deploy
            try:
                result = await self.deploy_provision(provision_id, server.fqdn)
                results.append(result)
                if result["success"]:
                    completed += 1
                else:
                    failed += 1
            except Exception as e:
                results.append({
                    "provision_id": provision_id,
                    "success": False,
                    "error": str(e),
                })
                failed += 1

        return {
            "total": len(provision_ids),
            "completed": completed,
            "failed": failed,
            "results": results,
        }
