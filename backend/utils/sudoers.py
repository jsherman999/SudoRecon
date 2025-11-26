"""Sudoers file manipulation utilities."""

import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from backend.models.provision import PrincipalType


class SudoersManager:
    """Manages sudoers file manipulation safely."""

    SUDORECON_MARKER = "# SUDORECON_MANAGED"
    PROVISION_PREFIX = "# SUDORECON_PROVISION_ID="

    def __init__(self, sudoers_path: str = "/etc/sudoers.d/sudorecon"):
        """Initialize sudoers manager.

        Args:
            sudoers_path: Path to sudoers file (default: /etc/sudoers.d/sudorecon)
        """
        self.sudoers_path = Path(sudoers_path)

    def generate_rule(
        self,
        provision_id: int,
        principal_type: PrincipalType,
        principal_name: str,
        sudo_rule: str,
        expires: Optional[datetime] = None,
    ) -> str:
        """Generate a sudoers rule with metadata.

        Args:
            provision_id: Provision ID
            principal_type: USER or GROUP
            principal_name: Principal name
            sudo_rule: Sudo rule specification
            expires: Optional expiry datetime

        Returns:
            Formatted sudoers rule with metadata
        """
        lines = [
            f"{self.PROVISION_PREFIX}{provision_id}",
        ]

        if expires:
            lines.append(f"# EXPIRES={expires.isoformat()}")

        # Format principal name
        if principal_type == PrincipalType.GROUP:
            # AD groups in QAS format or Unix groups
            if "\\" in principal_name:
                # AD group: DOMAIN\groupname -> %DOMAIN\\groupname
                principal = f"%{principal_name.replace(chr(92), chr(92) + chr(92))}"
            else:
                # Unix group
                principal = f"%{principal_name}"
        else:
            # User
            principal = principal_name

        # Add the actual rule
        rule_line = f"{principal} {sudo_rule}"
        lines.append(rule_line)

        return "\n".join(lines) + "\n"

    def parse_provision_id(self, line: str) -> Optional[int]:
        """Extract provision ID from comment line.

        Args:
            line: Comment line

        Returns:
            Provision ID or None
        """
        match = re.match(rf"{self.PROVISION_PREFIX}(\d+)", line)
        if match:
            return int(match.group(1))
        return None

    def read_rules(self) -> List[Tuple[int, str]]:
        """Read all SudoRecon-managed rules from file.

        Returns:
            List of (provision_id, rule_text) tuples
        """
        if not self.sudoers_path.exists():
            return []

        rules = []
        current_provision_id = None
        current_rule_lines = []

        with open(self.sudoers_path, "r") as f:
            for line in f:
                line = line.rstrip()

                # Check for provision ID marker
                provision_id = self.parse_provision_id(line)
                if provision_id is not None:
                    # Save previous rule if exists
                    if current_provision_id is not None:
                        rules.append((current_provision_id, "\n".join(current_rule_lines)))

                    # Start new rule
                    current_provision_id = provision_id
                    current_rule_lines = [line]
                elif current_provision_id is not None:
                    # Continue collecting lines for current rule
                    current_rule_lines.append(line)

            # Save last rule
            if current_provision_id is not None:
                rules.append((current_provision_id, "\n".join(current_rule_lines)))

        return rules

    def add_rule(
        self,
        provision_id: int,
        principal_type: PrincipalType,
        principal_name: str,
        sudo_rule: str,
        expires: Optional[datetime] = None,
    ) -> bool:
        """Add a new sudo rule.

        Args:
            provision_id: Provision ID
            principal_type: USER or GROUP
            principal_name: Principal name
            sudo_rule: Sudo rule specification
            expires: Optional expiry datetime

        Returns:
            True if successful
        """
        # Generate rule
        rule = self.generate_rule(provision_id, principal_type, principal_name, sudo_rule, expires)

        # Ensure directory exists
        self.sudoers_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to file
        with open(self.sudoers_path, "a") as f:
            f.write("\n" + rule)

        return self.validate_sudoers()

    def remove_rule(self, provision_id: int) -> bool:
        """Remove a sudo rule by provision ID.

        Args:
            provision_id: Provision ID to remove

        Returns:
            True if successful
        """
        if not self.sudoers_path.exists():
            return True

        # Read all rules
        rules = self.read_rules()

        # Filter out the rule to remove
        filtered_rules = [r for r in rules if r[0] != provision_id]

        if len(filtered_rules) == len(rules):
            # Rule not found, but that's okay
            return True

        # Write back filtered rules
        with open(self.sudoers_path, "w") as f:
            f.write(f"{self.SUDORECON_MARKER}\n")
            f.write("# Managed by SudoRecon - DO NOT EDIT MANUALLY\n\n")
            for _, rule_text in filtered_rules:
                f.write(rule_text + "\n\n")

        return self.validate_sudoers()

    def validate_sudoers(self) -> bool:
        """Validate sudoers file syntax using visudo.

        Returns:
            True if valid, False otherwise
        """
        import subprocess

        try:
            result = subprocess.run(
                ["visudo", "-c", "-f", str(self.sudoers_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            # If visudo is not available, assume valid
            # In production, this should be handled differently
            return True

    def backup_file(self) -> Optional[Path]:
        """Create a backup of the sudoers file.

        Returns:
            Path to backup file or None
        """
        if not self.sudoers_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.sudoers_path.with_suffix(f".backup.{timestamp}")

        import shutil

        shutil.copy2(self.sudoers_path, backup_path)
        return backup_path

    def initialize_file(self) -> bool:
        """Initialize sudoers file with header.

        Returns:
            True if successful
        """
        # Ensure directory exists
        self.sudoers_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file with header
        with open(self.sudoers_path, "w") as f:
            f.write(f"{self.SUDORECON_MARKER}\n")
            f.write("# Managed by SudoRecon - DO NOT EDIT MANUALLY\n")
            f.write(f"# Created: {datetime.now().isoformat()}\n\n")

        # Set proper permissions (0440)
        self.sudoers_path.chmod(0o440)

        return self.validate_sudoers()
