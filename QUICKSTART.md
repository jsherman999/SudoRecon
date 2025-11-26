# SudoRecon Quick Start Guide

This guide will help you get SudoRecon up and running quickly on RHEL 9.

## Choose Your Deployment Method

### Option 1: Development/Testing (Docker Compose)

The fastest way to try SudoRecon:

```bash
# Prerequisites: Docker and Docker Compose installed
git clone https://github.com/yourusername/SudoRecon.git
cd SudoRecon
cp .env.example .env
docker-compose up -d
```

Access the application:
- API: http://localhost:8080/api/docs
- Web UI: http://localhost:3000

### Option 2: Production (Python venv on RHEL 9)

See [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md#method-1-python-venv-deployment) for detailed instructions.

**Quick Summary:**

```bash
# Install dependencies
sudo dnf install -y python3.11 postgresql15-server redis nodejs

# Create service user
sudo useradd -r -m -d /opt/sudorecon -s /bin/bash sudorecon

# Clone and install
sudo su - sudorecon
git clone https://github.com/yourusername/SudoRecon.git app
cd app
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
exit

# Configure services (see full guide)
# Start services
sudo systemctl start sudorecon-api sudorecon-worker sudorecon-beat
```

### Option 3: Production (Podman on RHEL 9)

See [DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md#method-2-podman-deployment) for detailed instructions.

**Quick Summary:**

```bash
# Install Podman
sudo dnf install -y podman podman-compose

# Create user and deploy
sudo useradd -m sudorecon
sudo loginctl enable-linger sudorecon
sudo su - sudorecon

# Clone and start
git clone https://github.com/yourusername/SudoRecon.git
cd SudoRecon
cp .env.example .env
podman-compose up -d
```

## First Steps After Installation

### 1. Access the Web Interface

Navigate to http://your-server:3000 (or http://your-domain.com if using nginx)

### 2. Create Admin User

```bash
# venv method
sudo su - sudorecon
cd /opt/sudorecon/app
source venv/bin/activate
python scripts/create_admin.py
exit

# Podman method
podman exec -it sudorecon-api python scripts/create_admin.py
```

### 3. Add Your First Server

Using CLI:
```bash
sudorecon servers add server01.example.com
```

Using Web UI:
1. Go to "Servers" tab
2. Click "Add Server"
3. Enter hostname and details

### 4. Run Your First Scan

Using CLI:
```bash
sudorecon scan single server01.example.com
```

Using Web UI:
1. Go to "Scan" tab
2. Select server or group
3. Click "Start Scan"

### 5. Search Logs

Using CLI:
```bash
sudorecon logs search "systemctl" --limit 10
```

Using Web UI:
1. Go to "Logs" tab
2. Use search filters
3. View results

## Configuration Files

### Environment Variables (.env)

Key settings to configure:

```bash
# Database
DATABASE_URL=postgresql://sudorecon:password@localhost:5432/sudorecon

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your-secret-key-here

# SSH Access
SSH_USER=sudorecon
SSH_KEY_PATH=/opt/sudorecon/.ssh/id_rsa
```

## Common Tasks

### View Logs

```bash
# venv method
sudo journalctl -u sudorecon-api -f

# Podman method
podman logs -f sudorecon-api
```

### Restart Services

```bash
# venv method
sudo systemctl restart sudorecon-api

# Podman method
podman restart sudorecon-api
```

### Backup Database

```bash
# venv method
sudo -u postgres pg_dump sudorecon > backup.sql

# Podman method
podman exec sudorecon-db pg_dump -U sudorecon sudorecon > backup.sql
```

## Troubleshooting

### Check Service Status

```bash
# venv
sudo systemctl status sudorecon-api

# Podman
podman ps
```

### Connection Issues

1. Verify firewall: `sudo firewall-cmd --list-all`
2. Check SELinux: `sudo ausearch -m avc -ts recent`
3. Test database: `psql -h localhost -U sudorecon -d sudorecon`

### Enable Debug Mode

Edit `.env` or `/etc/sudorecon/.env`:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart services.

## Next Steps

- Read the full [Deployment Guide](DEPLOYMENT_RHEL9.md)
- Configure [SSH keys for target servers](DEPLOYMENT_RHEL9.md#set-up-ssh-keys)
- Set up [SSL/TLS certificates](DEPLOYMENT_RHEL9.md#configure-ssltls-production)
- Review [Security Hardening](DEPLOYMENT_RHEL9.md#security-hardening)

## Getting Help

- Documentation: [README.md](README.md)
- Technical Details: [Plan.md](Plan.md)
- Issues: https://github.com/yourusername/SudoRecon/issues

---

**Happy monitoring! 🚀**
