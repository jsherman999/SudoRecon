# SudoRecon - Rebranding Complete ✅

## Summary

Successfully rebranded application from **SudoGuard** to **SudoRecon**.

## Changes Made

### 1. Application Renaming

All occurrences of "SudoGuard" have been replaced with "SudoRecon" throughout the codebase:

- ✅ Application name
- ✅ CLI commands (`sudoguard` → `sudorecon`)
- ✅ Database names and users
- ✅ File paths and directories
- ✅ Service names
- ✅ Environment variable names
- ✅ Documentation

### 2. Files Modified

#### Core Application
- `backend/config.py` - App name, database URLs, SSH paths
- `backend/main.py` - Startup/shutdown messages
- `backend/tasks/celery_app.py` - Celery app name
- `backend/utils/sudoers.py` - Marker constants and file paths
- `cli/main.py` - CLI name, environment variables, help text
- `cli/commands/scan.py` - Environment variable references
- `pyproject.toml` - Package name, authors, entry points

#### Configuration
- `docker-compose.yml` - Container names, database config, volumes
- `Dockerfile.api` - Directory paths
- `alembic.ini` - Database connection string
- `frontend/index.html` - Page title

#### Documentation
- `README.md` - All command examples and references
- `Plan.md` - Complete technical design document

### 3. New Documentation Created

#### DEPLOYMENT_RHEL9.md
Comprehensive deployment guide with two methods:

1. **Python venv Method**
   - System dependencies installation
   - PostgreSQL 15 setup
   - Redis configuration
   - Python virtual environment
   - Systemd service units
   - Nginx reverse proxy
   - SSL/TLS with Let's Encrypt
   - Firewall configuration
   - SELinux setup

2. **Podman Method**
   - Rootless container deployment
   - Podman Compose configuration
   - Systemd user services
   - Container orchestration
   - Volume management

**Features:**
- Step-by-step instructions
- Production-ready configurations
- Security hardening guidelines
- Performance tuning tips
- Monitoring and maintenance procedures
- Comprehensive troubleshooting guide
- Database backup procedures
- Update/upgrade procedures

#### QUICKSTART.md
Quick reference guide including:
- Fast deployment options
- First steps after installation
- Common tasks
- Quick troubleshooting
- Configuration reference

#### CHANGELOG.md
- Complete list of all changes
- Migration guide from SudoGuard
- Version history
- Breaking changes documentation

## Configuration Changes Required

### Environment Variables

**Old:**
```bash
SUDOGUARD_API_KEY=...
DATABASE_URL=postgresql://sudoguard:secret@localhost:5432/sudoguard
SSH_USER=sudoguard
SSH_KEY_PATH=/home/sudoguard/.ssh/id_rsa
SSH_CONTROL_PATH=/var/run/sudoguard/ssh-%r@%h:%p
```

**New:**
```bash
SUDORECON_API_KEY=...
DATABASE_URL=postgresql://sudorecon:secret@localhost:5432/sudorecon
SSH_USER=sudorecon
SSH_KEY_PATH=/home/sudorecon/.ssh/id_rsa
SSH_CONTROL_PATH=/var/run/sudorecon/ssh-%r@%h:%p
```

### Service Names

**Old:**
- `sudoguard-api.service`
- `sudoguard-worker.service`
- `sudoguard-beat.service`
- `sudoguard-frontend` (container)
- `sudoguard-db` (container)
- `sudoguard-redis` (container)

**New:**
- `sudorecon-api.service`
- `sudorecon-worker.service`
- `sudorecon-beat.service`
- `sudorecon-frontend` (container)
- `sudorecon-db` (container)
- `sudorecon-redis` (container)

### File Paths

**Old:**
- `/opt/sudoguard/`
- `/etc/sudoguard/`
- `/var/log/sudoguard/`
- `/var/run/sudoguard/`
- `/etc/sudoers.d/sudoguard`

**New:**
- `/opt/sudorecon/`
- `/etc/sudorecon/`
- `/var/log/sudorecon/`
- `/var/run/sudorecon/`
- `/etc/sudoers.d/sudorecon`

### CLI Commands

**Old:**
```bash
sudoguard servers list
sudoguard scan single server01
sudoguard logs search "command"
sudoguard provision grant --server 1 --user alice
```

**New:**
```bash
sudorecon servers list
sudorecon scan single server01
sudorecon logs search "command"
sudorecon provision grant --server 1 --user alice
```

## Deployment Options

### Option 1: Development with Docker Compose
```bash
git clone <repo>
cd SudoRecon
cp .env.example .env
docker-compose up -d
```

Access:
- API: http://localhost:8080/api/docs
- Web UI: http://localhost:3000

### Option 2: Production on RHEL 9 (venv)
See [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md#method-1-python-venv-deployment)

Key steps:
1. Install dependencies (Python 3.11, PostgreSQL 15, Redis, Node.js 20)
2. Create service user `sudorecon`
3. Set up databases
4. Install application in venv
5. Configure systemd services
6. Set up nginx reverse proxy
7. Configure SSL/TLS

### Option 3: Production on RHEL 9 (Podman)
See [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md#method-2-podman-deployment)

Key steps:
1. Install Podman
2. Create service user with lingering enabled
3. Clone repository
4. Configure .env file
5. Start containers with podman-compose
6. Configure systemd user services
7. Set up nginx reverse proxy (optional)

## Next Steps

1. **Review Documentation**
   - Read [README.md](README.md) for overview
   - Review [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md) for deployment details
   - Check [QUICKSTART.md](QUICKSTART.md) for quick reference

2. **Set Up SSH Keys**
   - Generate SSH keys for sudorecon user
   - Distribute public keys to target servers
   - Configure SSH ControlMaster settings

3. **Initial Configuration**
   - Update .env file with production credentials
   - Generate strong JWT secret
   - Configure database passwords
   - Set up Redis authentication (if needed)

4. **Security Hardening**
   - Configure firewall rules
   - Set up SELinux policies
   - Enable SSL/TLS
   - Implement API rate limiting
   - Regular security updates

5. **Monitoring Setup**
   - Configure log rotation
   - Set up system monitoring
   - Implement backup procedures
   - Create alerting rules

## Testing Checklist

- [ ] Application starts successfully
- [ ] Database migrations run without errors
- [ ] API endpoints respond correctly
- [ ] CLI commands work with new names
- [ ] Web UI loads and functions
- [ ] SSH connections to target servers work
- [ ] Log scanning completes successfully
- [ ] Provisions can be created and deployed
- [ ] Celery tasks execute properly
- [ ] Background jobs process correctly

## Support

For issues or questions:
- Review [Troubleshooting Guide](DEPLOYMENT_RHEL9.md#troubleshooting)
- Check [GitHub Issues](https://github.com/yourusername/SudoRecon/issues)
- Consult [Technical Design](Plan.md)

## References

- [README.md](README.md) - Project overview
- [Plan.md](Plan.md) - Technical design document
- [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md) - Deployment guide
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [CHANGELOG.md](CHANGELOG.md) - Change history

---

**Rebranding Completed:** November 25, 2025  
**Version:** 1.0.0  
**Status:** ✅ Ready for deployment
