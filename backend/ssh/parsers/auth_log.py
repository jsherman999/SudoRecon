"""Parser for auth.log and secure log files."""

import re
from datetime import datetime
from typing import Dict, List, Optional

from dateutil import parser as date_parser


class AuthLogParser:
    """Parser for auth.log and /var/log/secure files."""

    # Pattern for standard syslog sudo entries
    PATTERN = re.compile(
        r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<hostname>\S+)\s+"
        r"sudo:\s+"
        r"(?P<username>\S+)\s+:\s+"
        r"(TTY=(?P<tty>\S+)\s*;\s*)?"
        r"PWD=(?P<pwd>[^;]+?)\s*;\s+"
        r"USER=(?P<runas>\S+)\s*;\s+"
        r"COMMAND=(?P<command>.+)$"
    )

    # Pattern for denied commands
    DENY_PATTERN = re.compile(
        r"(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<hostname>\S+)\s+"
        r"sudo:\s+"
        r"(?P<username>\S+)\s+:\s+"
        r".*?command not allowed"
    )

    def __init__(self, current_year: Optional[int] = None):
        """Initialize parser.

        Args:
            current_year: Year to use for syslog timestamps (defaults to current year)
        """
        self.current_year = current_year or datetime.now().year

    def parse_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a single log line.

        Args:
            line: Raw log line

        Returns:
            Parsed log entry as dict, or None if line doesn't match
        """
        # Try to match standard sudo entry
        match = self.PATTERN.match(line)
        if match:
            data = match.groupdict()
            # Parse timestamp (syslog format doesn't include year)
            timestamp_str = f"{data['timestamp']} {self.current_year}"
            try:
                timestamp = date_parser.parse(timestamp_str)
            except Exception:
                timestamp = datetime.now()

            return {
                "timestamp": timestamp.isoformat(),
                "username": data["username"],
                "tty": data.get("tty") or None,
                "pwd": data.get("pwd") or None,
                "runas_user": data.get("runas") or "root",
                "command": data["command"],
                "result": "ACCEPT",
                "raw_log": line.strip(),
            }

        # Try to match deny entry
        deny_match = self.DENY_PATTERN.match(line)
        if deny_match:
            data = deny_match.groupdict()
            timestamp_str = f"{data['timestamp']} {self.current_year}"
            try:
                timestamp = date_parser.parse(timestamp_str)
            except Exception:
                timestamp = datetime.now()

            return {
                "timestamp": timestamp.isoformat(),
                "username": data["username"],
                "tty": None,
                "pwd": None,
                "runas_user": None,
                "command": "unknown",
                "result": "DENY",
                "raw_log": line.strip(),
            }

        return None

    def parse_file(self, content: str) -> List[Dict[str, str]]:
        """Parse entire log file content.

        Args:
            content: Raw log file content

        Returns:
            List of parsed log entries
        """
        entries = []
        for line in content.splitlines():
            if "sudo:" not in line:
                continue

            entry = self.parse_line(line)
            if entry:
                entries.append(entry)

        return entries
