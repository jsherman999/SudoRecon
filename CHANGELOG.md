# Changelog

All notable changes to the SudoRecon project will be documented in this file.

## [1.0.0] - 2025-11-25

### Changed

- **BREAKING**: Renamed application from "SudoGuard" to "SudoRecon"
  - Updated all configuration files
  - Updated CLI command from `sudoguard` to `sudorecon`
  - Updated API command from `sudoguard-api` to `sudorecon-api`
  - Updated all database connection strings
  - Updated all service user references
  - Updated all file paths and directories
  - Updated all documentation

### Added

- Comprehensive RHEL 9 deployment guide (`DEPLOYMENT_RHEL9.md`)
  - Python venv deployment method with systemd services
  - Podman container deployment method
  - Complete PostgreSQL, Redis, and application setup
  - Firewall and SELinux configuration
  - Production nginx reverse proxy setup
  - SSL/TLS configuration with Let's Encrypt
  - Monitoring and maintenance procedures
  - Troubleshooting guide
  - Security hardening recommendations
  - Performance tuning tips
  
- Quick start guide (`QUICKSTART.md`)
  - Fast deployment instructions for all methods
  - First steps after installation
  - Common tasks reference
  - Quick troubleshooting

### Migration Guide

If you have an existing SudoGuard installation, follow these steps to migrate to SudoRecon:

#### Database Migration

```sql
-- No database schema changes required
-- Only configuration references need to be updated
```

#### Configuration Files

1. Update environment variables:
   ```bash
   # Old
   SUDOGUARD_API_KEY=...
   
   # New
   SUDORECON_API_KEY=...
   ```

2. Update database user and database name (if following conventions):
   ```sql
   ALTER USER sudoguard RENAME TO sudorecon;
   ALTER DATABASE sudoguard RENAME TO sudorecon;
   ```

3. Update SSH paths:
   ```bash
   # Old
   SSH_CONTROL_PATH=/var/run/sudoguard/ssh-%r@%h:%p
   SSH_KEY_PATH=/home/sudoguard/.ssh/id_rsa
   
   # New
   SSH_CONTROL_PATH=/var/run/sudorecon/ssh-%r@%h:%p
   SSH_KEY_PATH=/home/sudorecon/.ssh/id_rsa
   ```

4. Update systemd service files:
   ```bash
   # Rename service files
   sudo mv /etc/systemd/system/sudoguard-api.service /etc/systemd/system/sudorecon-api.service
   sudo mv /etc/systemd/system/sudoguard-worker.service /etc/systemd/system/sudorecon-worker.service
   sudo mv /etc/systemd/system/sudoguard-beat.service /etc/systemd/system/sudorecon-beat.service
   
   # Edit each file and update User, Group, WorkingDirectory, and EnvironmentFile paths
   
   # Reload systemd
   sudo systemctl daemon-reload
   ```

5. Update file system paths:
   ```bash
   # Move installation directory
   sudo mv /opt/sudoguard /opt/sudorecon
   
   # Move config directory
   sudo mv /etc/sudoguard /etc/sudorecon
   
   # Move log directory
   sudo mv /var/log/sudoguard /var/log/sudorecon
   
   # Move runtime directory
   sudo mv /var/run/sudoguard /var/run/sudorecon
   ```

6. Update user and group (if desired):
   ```bash
   # Rename user
   sudo usermod -l sudorecon sudoguard
   sudo groupmod -n sudorecon sudoguard
   
   # Update home directory
   sudo usermod -d /opt/sudorecon -m sudorecon
   ```

#### CLI Update

```bash
# Uninstall old CLI
pip uninstall sudoguard

# Install new CLI
pip install -e .

# New command syntax
sudorecon --help
```

### Files Changed

#### Core Application Files
- `backend/config.py` - Updated app name and default paths
- `backend/tasks/celery_app.py` - Updated Celery app name
- `cli/main.py` - Updated CLI command name and help text
- `pyproject.toml` - Updated package name and entry points

#### Configuration Files
- `docker-compose.yml` - Updated container names, database names, user names, and paths
- `alembic.ini` - Updated database connection string
- `Dockerfile.api` - Updated directory paths
- `.env.example` - Updated all references (if exists)

#### Documentation Files
- `README.md` - Updated all references to app name and commands
- `Plan.md` - Updated comprehensive technical design document
- `frontend/index.html` - Updated page title

#### New Files
- `DEPLOYMENT_RHEL9.md` - Complete deployment guide
- `QUICKSTART.md` - Quick start guide
- `CHANGELOG.md` - This file

### Notes

- All functionality remains the same
- No breaking changes to API endpoints or database schema
- Only naming and configuration paths have changed
- Existing data is compatible with the renamed application

---

## [0.9.0] - 2024-XX-XX (Previous Version as SudoGuard)

### Completed Features

#### Phase 1: Foundation
- [x] Project scaffolding and structure
- [x] Database schema (PostgreSQL + SQLAlchemy)
- [x] Core API framework (FastAPI)
- [x] SSH connection manager (asyncssh + ControlMaster)
- [x] Basic CLI (Click framework)

#### Phase 2: Core Features
- [x] Log parsing engine (auth.log, secure, sudo.log)
- [x] Single-host scanning
- [x] Parallel scanning support
- [x] Log search API with filters
- [x] Basic web UI (React + TypeScript)

#### Phase 3: Provisioning
- [x] Sudoers manipulation - Safe file editing with validation
- [x] Provision API - Full CRUD operations
- [x] Provision service - Deployment and revocation via SSH
- [x] JIT access - Time-limited grants with auto-expiry
- [x] Bulk provisioning - Parallel deployment across servers
- [x] Provision CLI - Grant, revoke, list, JIT commands
- [x] Celery tasks - Background processing and maintenance

#### Phase 4: Advanced Features
- [x] Real-time updates - SSE streaming for scan job progress
- [x] Export functionality - CSV/JSON log exports
- [x] Audit logging - Comprehensive action tracking
- [x] Enhanced dashboard - Statistics and recent activity
- [x] Expiring provisions - Automatic detection and alerts
- [x] Provision history - Complete audit trail

---

For more information, see the [README](README.md) or visit the project repository.
