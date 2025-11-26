# SudoRecon

Centralized sudo management and log analysis platform.

## Overview

SudoRecon provides comprehensive sudo log collection, analysis, and access provisioning across your infrastructure through three interfaces:

- **REST API** - FastAPI-based backend for programmatic access
- **CLI Tool** - Command-line interface for interactive use
- **Web Dashboard** - Modern React-based web interface

## Implementation Status

### ✅ Phase 1: Foundation (Complete)
- [x] Project scaffolding and structure
- [x] Database schema (PostgreSQL + SQLAlchemy)
- [x] Core API framework (FastAPI)
- [x] SSH connection manager (asyncssh + ControlMaster)
- [x] Basic CLI (Click framework)

### ✅ Phase 2: Core Features (Complete)
- [x] Log parsing engine (auth.log, secure, sudo.log)
- [x] Single-host scanning
- [x] Parallel scanning support
- [x] Log search API with filters
- [x] Basic web UI (React + TypeScript)

### ✅ Phase 3: Provisioning (Complete)
- [x] Sudoers manipulation - Safe file editing with validation
- [x] Provision API - Full CRUD operations
- [x] Provision service - Deployment and revocation via SSH
- [x] JIT access - Time-limited grants with auto-expiry
- [x] Bulk provisioning - Parallel deployment across servers
- [x] Provision CLI - Grant, revoke, list, JIT commands
- [x] Celery tasks - Background processing and maintenance

### ✅ Phase 4: Advanced Features (Complete)
- [x] Real-time updates - SSE streaming for scan job progress
- [x] Export functionality - CSV/JSON log exports
- [x] Audit logging - Comprehensive action tracking
- [x] Enhanced dashboard - Statistics and recent activity
- [x] Expiring provisions - Automatic detection and alerts
- [x] Provision history - Complete audit trail

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Services will be available at:
- API: http://localhost:8080
- Web UI: http://localhost:3000
- API Docs: http://localhost:8080/api/docs

### Deployment on RHEL 9

For production deployment on RHEL 9, see our comprehensive deployment guide:

**[📖 DEPLOYMENT_RHEL9.md](DEPLOYMENT_RHEL9.md)**

Two deployment methods available:
1. **Python venv** - Traditional deployment with systemd services
2. **Podman** - Containerized deployment with rootless containers

Quick start guide also available: **[🚀 QUICKSTART.md](QUICKSTART.md)**

### Manual Setup

1. **Install backend dependencies:**

```bash
pip install -e .
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start PostgreSQL and Redis:**

```bash
# Using Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=secret postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

4. **Run database migrations:**

```bash
alembic upgrade head
```

5. **Start the API server:**

```bash
python -m uvicorn backend.main:app --reload
```

6. **Install frontend dependencies and start dev server:**

```bash
cd frontend
npm install
npm run dev
```

## CLI Usage

### Server Management

```bash
# List servers
sudorecon servers list

# Add a server
sudorecon servers add webserver01.example.com

# Remove a server
sudorecon servers remove 1
```

### Scanning

```bash
# Scan a single server
sudorecon scan single webserver01.example.com

# Scan a server group
sudorecon scan group 1 --threads 50

# Check scan job status
sudorecon scan status <job-id>
```

### Log Search

```bash
# Search logs
sudorecon logs search "systemctl restart"

# Filter by user
sudorecon logs search --user jsmith

# Filter by result
sudorecon logs search --result DENY

# View statistics
sudorecon logs stats
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8080/api/docs
- ReDoc: http://localhost:8080/api/redoc

### Example API Requests

```bash
# List servers
curl -H "X-API-Key: your-key" http://localhost:8080/api/v1/servers

# Start a scan
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"hostname": "webserver01.example.com"}' \
  http://localhost:8080/api/v1/scan/single

# Search logs
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/api/v1/logs?username=admin&page_size=10"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SUDORECON PLATFORM                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │  Web UI  │    │   CLI    │    │   External Systems   │  │
│  └────┬─────┘    └────┬─────┘    └──────────┬───────────┘  │
│       │               │                      │              │
│       └───────────────┼──────────────────────┘              │
│                       ▼                                     │
│           ┌────────────────────────┐                        │
│           │     REST API           │                        │
│           │     (FastAPI)          │                        │
│           └───────┬────────────────┘                        │
│                   │                                         │
│       ┌───────────┼───────────────┐                         │
│       ▼           ▼               ▼                         │
│  ┌────────┐  ┌────────┐    ┌──────────┐                    │
│  │  SSH   │  │ Celery │    │PostgreSQL│                    │
│  │  Pool  │  │ Tasks  │    │  + Redis │                    │
│  └────────┘  └────────┘    └──────────┘                    │
│       │                                                     │
└───────┼─────────────────────────────────────────────────────┘
        │
        ▼
   Target Servers
```

## Database Schema

See `Plan.md` for detailed schema documentation.

Key tables:
- `servers` - Server inventory
- `server_groups` - Logical server groupings
- `sudo_logs` - Collected sudo log entries
- `sudo_provisions` - Access grants and permissions
- `scan_jobs` - Background scan job tracking

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=backend tests/
```

### Code Quality

```bash
# Format code
black backend cli

# Lint
ruff backend cli

# Type checking
mypy backend
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

Configuration is managed through environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `SSH_USER` | `sudorecon` | SSH username for connections |
| `SSH_KEY_PATH` | `/home/sudorecon/.ssh/id_rsa` | Path to SSH private key |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `API_PORT` | `8080` | API server port |

See `.env.example` for all available options.

## Security Considerations

- API key authentication required for all endpoints
- SSH connections use key-based authentication
- Database credentials should be rotated regularly
- TLS encryption recommended for production deployments
- Audit logs track all user actions

## License

MIT

## Contributors

SudoRecon Team

## Support

For issues and questions, please open an issue on GitHub.

### Provision Management

```bash
# List provisions
sudorecon provision list

# Grant sudo to a user
sudorecon provision grant \
  --server 1 \
  --user jsmith \
  --rule "ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx" \
  --expires "2024-12-31" \
  --justification "Monthly maintenance" \
  --ticket CHG0012345

# Grant JIT access
sudorecon provision jit \
  --server 1 \
  --user emergency_user \
  --duration 60 \
  --justification "Emergency production issue"

# Revoke a provision
sudorecon provision revoke 101 --reason "Access no longer needed"

# Check expiring provisions
sudorecon provision expiring --hours 24
```


### Provision API

```bash
# List provisions
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/api/v1/provisions?status=active"

# Create provision
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "servers": [1, 2, 3],
    "principal_type": "user",
    "principal_name": "jsmith",
    "sudo_rule": "ALL=(ALL) NOPASSWD: /usr/bin/systemctl",
    "grant_end": "2024-12-31T23:59:59Z",
    "justification": "Maintenance access"
  }' \
  http://localhost:8080/api/v1/provisions

# Create JIT access
curl -X POST -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": 1,
    "principal_type": "user",
    "principal_name": "jsmith",
    "duration_minutes": 60,
    "justification": "Emergency access"
  }' \
  http://localhost:8080/api/v1/provisions/jit

# Export logs
curl -H "X-API-Key: your-key" \
  "http://localhost:8080/api/v1/logs/export?format=csv&username=jsmith" \
  -o sudo_logs.csv
```

