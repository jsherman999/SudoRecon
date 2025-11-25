# SudoGuard

Centralized sudo management and log analysis platform.

## Overview

SudoGuard provides comprehensive sudo log collection, analysis, and access provisioning across your infrastructure through three interfaces:

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

### 🚧 Phase 3: Provisioning (Planned)
- [ ] Sudoers manipulation
- [ ] Provision API (create, revoke)
- [ ] AD/QAS integration
- [ ] JIT access
- [ ] Bulk provisioning

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
sudoguard servers list

# Add a server
sudoguard servers add webserver01.example.com

# Remove a server
sudoguard servers remove 1
```

### Scanning

```bash
# Scan a single server
sudoguard scan single webserver01.example.com

# Scan a server group
sudoguard scan group 1 --threads 50

# Check scan job status
sudoguard scan status <job-id>
```

### Log Search

```bash
# Search logs
sudoguard logs search "systemctl restart"

# Filter by user
sudoguard logs search --user jsmith

# Filter by result
sudoguard logs search --result DENY

# View statistics
sudoguard logs stats
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
│                      SUDOGUARD PLATFORM                      │
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
| `SSH_USER` | `sudoguard` | SSH username for connections |
| `SSH_KEY_PATH` | `/home/sudoguard/.ssh/id_rsa` | Path to SSH private key |
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

SudoGuard Team

## Support

For issues and questions, please open an issue on GitHub.
