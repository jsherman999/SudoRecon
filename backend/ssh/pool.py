"""SSH connection pool manager."""

import asyncio
from typing import Any, Callable, Dict, List, Optional

import asyncssh

from backend.config import get_settings

settings = get_settings()


class SSHPoolManager:
    """Manages a pool of SSH connections with multiplexing support."""

    def __init__(
        self,
        max_concurrent: int = 100,
        timeout: int = 30,
        ssh_user: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
    ):
        """Initialize SSH pool manager.

        Args:
            max_concurrent: Maximum number of concurrent connections
            timeout: Connection timeout in seconds
            ssh_user: SSH username (defaults to settings)
            ssh_key_path: Path to SSH private key (defaults to settings)
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.ssh_user = ssh_user or settings.ssh_user
        self.ssh_key_path = ssh_key_path or settings.ssh_key_path
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.connections: Dict[str, Any] = {}

    async def execute_on_host(
        self, hostname: str, command: str
    ) -> Dict[str, Any]:
        """Execute a command on a single host.

        Args:
            hostname: Target hostname
            command: Command to execute

        Returns:
            Dict with stdout, stderr, exit_code, and error info
        """
        async with self.semaphore:
            try:
                async with asyncssh.connect(
                    hostname,
                    username=self.ssh_user,
                    client_keys=[self.ssh_key_path],
                    known_hosts=None,  # For development; use proper known_hosts in production
                    connect_timeout=self.timeout,
                ) as conn:
                    result = await conn.run(command, check=False, timeout=self.timeout)

                    return {
                        "hostname": hostname,
                        "success": True,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "exit_code": result.exit_status,
                        "error": None,
                    }

            except asyncio.TimeoutError:
                return {
                    "hostname": hostname,
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": "Connection timeout",
                }
            except asyncssh.Error as e:
                return {
                    "hostname": hostname,
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": f"SSH error: {str(e)}",
                }
            except Exception as e:
                return {
                    "hostname": hostname,
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "error": f"Unexpected error: {str(e)}",
                }

    async def execute_on_hosts(
        self,
        hostnames: List[str],
        command: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Execute command on multiple hosts concurrently.

        Args:
            hostnames: List of target hostnames
            command: Command to execute
            progress_callback: Optional callback for progress updates

        Returns:
            List of execution results
        """
        tasks = []
        for hostname in hostnames:
            task = self.execute_on_host(hostname, command)
            tasks.append(task)

        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(hostnames), result)

        return results

    async def read_file_from_host(
        self, hostname: str, file_path: str
    ) -> Dict[str, Any]:
        """Read a file from a remote host.

        Args:
            hostname: Target hostname
            file_path: Path to file on remote host

        Returns:
            Dict with file content or error
        """
        command = f"cat {file_path}"
        return await self.execute_on_host(hostname, command)

    async def check_connectivity(self, hostname: str) -> bool:
        """Check if a host is reachable via SSH.

        Args:
            hostname: Target hostname

        Returns:
            True if reachable, False otherwise
        """
        result = await self.execute_on_host(hostname, "echo OK")
        return result["success"] and result["stdout"].strip() == "OK"
