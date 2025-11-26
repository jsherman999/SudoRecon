# Sudo Log Analyzer & Deployment Application

## Comprehensive Technical Design Document

-----

## 1. Executive Summary

This document outlines the complete design for **SudoRecon**, a centralized sudo management platform that provides:

- **Log Analysis**: Real-time and historical sudo log collection, parsing, and analysis
- **Provisioning**: Just-in-time (JIT) and scheduled sudo access grants for users and AD groups
- **Multi-Server Operations**: Parallel execution across thousands of servers via SSH multiplexing
- **Triple Interface**: REST API, CLI tool, and modern web dashboard

The application runs on a jump server with pre-established passwordless SSH access to all target hosts, which are domain-joined via Quest Authentication Services (QAS/VAS).

-----

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUDORECON PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │   Web UI     │    │     CLI      │    │        External Systems      │  │
│  │  (React/Vue) │    │   (Python)   │    │   (SIEM, Ticketing, etc.)   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┬───────────────┘  │
│         │                   │                           │                   │
│         └───────────────────┼───────────────────────────┘                   │
│                             │                                               │
│                             ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         REST API (FastAPI)                            │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │  │
│  │  │   /scan     │ │ /provision  │ │   /logs     │ │    /reports     │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                             │                                               │
│         ┌───────────────────┼───────────────────┐                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐    │
│  │   Task      │    │   SSH       │    │        Database             │    │
│  │   Queue     │    │   Pool      │    │   (PostgreSQL + Redis)      │    │
│  │  (Celery)   │    │  Manager    │    │                             │    │
│  └──────┬──────┘    └──────┬──────┘    └─────────────────────────────┘    │
│         │                  │                                               │
│         └────────┬─────────┘                                               │
│                  ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    SSH Connection Manager                             │  │
│  │         (ControlMaster Multiplexing + Async Workers)                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────────────┐
        │                      TARGET SERVERS                             │
        │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
        │  │ Server1 │ │ Server2 │ │ Server3 │ │   ...   │ │ ServerN │  │
        │  │  (QAS)  │ │  (QAS)  │ │  (QAS)  │ │         │ │  (QAS)  │  │
        │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
        └────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Stack

|Layer       |Technology                      |Purpose                                      |
|------------|--------------------------------|---------------------------------------------|
|Web Frontend|React 18 + TypeScript           |Modern SPA with terminal aesthetics          |
|API Server  |FastAPI (Python 3.11+)          |Async REST endpoints with OpenAPI            |
|Task Queue  |Celery + Redis                  |Background job processing                    |
|Database    |PostgreSQL 15                   |Primary data store                           |
|Cache/Broker|Redis 7                         |Session cache, task broker, real-time pub/sub|
|SSH Layer   |asyncssh + OpenSSH ControlMaster|High-performance parallel connections        |
|CLI         |Click (Python)                  |Command-line interface                       |

-----

## 3. Database Schema

### 3.1 Entity Relationship Diagram

```
┌─────────────────────────┐       ┌─────────────────────────┐
│        servers          │       │      server_groups      │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ hostname                │◄──────│ name                    │
│ fqdn                    │       │ description             │
│ ip_address              │       │ created_at              │
│ domain                  │       │ updated_at              │
│ os_version              │       └─────────────────────────┘
│ last_scan_at            │                │
│ status                  │                │
│ created_at              │       ┌────────┴────────┐
│ updated_at              │       │ server_group_   │
└─────────────────────────┘       │   members       │
          │                       ├─────────────────┤
          │                       │ server_id (FK)  │
          │                       │ group_id (FK)   │
          ▼                       └─────────────────┘
┌─────────────────────────┐
│      sudo_logs          │
├─────────────────────────┤
│ id (PK)                 │
│ server_id (FK)          │
│ timestamp               │
│ username                │
│ tty                     │
│ pwd                     │
│ runas_user              │
│ command                 │
│ result (ACCEPT/DENY)    │
│ raw_log                 │
│ session_id              │
│ created_at              │
└─────────────────────────┘
          │
          │
┌─────────────────────────┐       ┌─────────────────────────┐
│    sudo_provisions      │       │    provision_history    │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK)                 │──────►│ id (PK)                 │
│ server_id (FK)          │       │ provision_id (FK)       │
│ principal_type          │       │ action                  │
│ principal_name          │       │ performed_by            │
│ sudo_rule               │       │ details (JSONB)         │
│ is_jit                  │       │ created_at              │
│ grant_start             │       └─────────────────────────┘
│ grant_end               │
│ status                  │
│ justification           │
│ approved_by             │
│ ticket_reference        │
│ created_at              │
│ updated_at              │
└─────────────────────────┘

┌─────────────────────────┐       ┌─────────────────────────┐
│      scan_jobs          │       │      audit_log          │
├─────────────────────────┤       ├─────────────────────────┤
│ id (PK, UUID)           │       │ id (PK)                 │
│ job_type                │       │ user_id                 │
│ target_type             │       │ action                  │
│ target_spec             │       │ resource_type           │
│ thread_count            │       │ resource_id             │
│ status                  │       │ old_value (JSONB)       │
│ progress                │       │ new_value (JSONB)       │
│ total_hosts             │       │ ip_address              │
│ completed_hosts         │       │ user_agent              │
│ failed_hosts            │       │ created_at              │
│ started_at              │       └─────────────────────────┘
│ completed_at            │
│ created_by              │
│ created_at              │
└─────────────────────────┘

┌─────────────────────────┐
│        users            │
├─────────────────────────┤
│ id (PK)                 │
│ username                │
│ email                   │
│ display_name            │
│ role                    │
│ api_key_hash            │
│ last_login              │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
```

### 3.2 SQL Schema Definition

```sql
-- Core tables
CREATE TYPE server_status AS ENUM ('active', 'unreachable', 'maintenance', 'decommissioned');
CREATE TYPE provision_status AS ENUM ('pending', 'active', 'expired', 'revoked');
CREATE TYPE principal_type AS ENUM ('user', 'group');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE user_role AS ENUM ('viewer', 'operator', 'admin', 'superadmin');

CREATE TABLE servers (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    fqdn VARCHAR(512) UNIQUE NOT NULL,
    ip_address INET,
    domain VARCHAR(255),
    os_version VARCHAR(128),
    last_scan_at TIMESTAMP WITH TIME ZONE,
    status server_status DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE server_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE server_group_members (
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES server_groups(id) ON DELETE CASCADE,
    PRIMARY KEY (server_id, group_id)
);

CREATE TABLE sudo_logs (
    id BIGSERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    username VARCHAR(255) NOT NULL,
    tty VARCHAR(64),
    pwd VARCHAR(1024),
    runas_user VARCHAR(255),
    command TEXT NOT NULL,
    result VARCHAR(16) NOT NULL,  -- 'ACCEPT' or 'DENY'
    raw_log TEXT,
    session_id VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE sudo_provisions (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id) ON DELETE CASCADE,
    principal_type principal_type NOT NULL,
    principal_name VARCHAR(512) NOT NULL,
    sudo_rule TEXT NOT NULL,
    is_jit BOOLEAN DEFAULT FALSE,
    grant_start TIMESTAMP WITH TIME ZONE NOT NULL,
    grant_end TIMESTAMP WITH TIME ZONE,
    status provision_status DEFAULT 'pending',
    justification TEXT,
    approved_by VARCHAR(255),
    ticket_reference VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE provision_history (
    id BIGSERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES sudo_provisions(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE scan_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(64) NOT NULL,  -- 'log_scan', 'provision', 'revoke'
    target_type VARCHAR(32) NOT NULL,  -- 'single', 'group', 'file'
    target_spec TEXT NOT NULL,  -- hostname, group name, or file path/content
    thread_count INTEGER DEFAULT 10,
    status job_status DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_hosts INTEGER DEFAULT 0,
    completed_hosts INTEGER DEFAULT 0,
    failed_hosts INTEGER DEFAULT 0,
    error_details JSONB DEFAULT '[]',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    display_name VARCHAR(255),
    role user_role DEFAULT 'viewer',
    api_key_hash VARCHAR(128),
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_sudo_logs_server_timestamp ON sudo_logs(server_id, timestamp DESC);
CREATE INDEX idx_sudo_logs_username ON sudo_logs(username);
CREATE INDEX idx_sudo_logs_command_gin ON sudo_logs USING gin(to_tsvector('english', command));
CREATE INDEX idx_sudo_logs_raw_log_gin ON sudo_logs USING gin(to_tsvector('english', raw_log));
CREATE INDEX idx_provisions_status ON sudo_provisions(status);
CREATE INDEX idx_provisions_grant_end ON sudo_provisions(grant_end) WHERE status = 'active';
CREATE INDEX idx_servers_fqdn ON servers(fqdn);
CREATE INDEX idx_scan_jobs_status ON scan_jobs(status);
```

-----

## 4. API Specification

### 4.1 API Overview

Base URL: `/api/v1`

Authentication: API Key (header: `X-API-Key`) or JWT Bearer Token

### 4.2 Endpoint Groups

#### 4.2.1 Server Management

|Method|Endpoint                  |Description                               |
|------|--------------------------|------------------------------------------|
|GET   |`/servers`                |List all servers with pagination/filtering|
|GET   |`/servers/{id}`           |Get server details                        |
|POST  |`/servers`                |Register a new server                     |
|PUT   |`/servers/{id}`           |Update server information                 |
|DELETE|`/servers/{id}`           |Remove server from inventory              |
|GET   |`/servers/{id}/provisions`|List active provisions for server         |
|GET   |`/servers/{id}/logs`      |Get sudo logs for server                  |

#### 4.2.2 Server Groups

|Method|Endpoint                          |Description             |
|------|----------------------------------|------------------------|
|GET   |`/groups`                         |List all server groups  |
|POST  |`/groups`                         |Create a new group      |
|PUT   |`/groups/{id}`                    |Update group details    |
|DELETE|`/groups/{id}`                    |Delete group            |
|POST  |`/groups/{id}/members`            |Add servers to group    |
|DELETE|`/groups/{id}/members/{server_id}`|Remove server from group|

#### 4.2.3 Scanning Operations

|Method|Endpoint                |Description                     |
|------|------------------------|--------------------------------|
|POST  |`/scan/single`          |Scan a single server            |
|POST  |`/scan/group`           |Scan all servers in a group     |
|POST  |`/scan/file`            |Scan servers from uploaded file |
|GET   |`/scan/jobs`            |List all scan jobs              |
|GET   |`/scan/jobs/{id}`       |Get scan job status and results |
|DELETE|`/scan/jobs/{id}`       |Cancel a running scan job       |
|GET   |`/scan/jobs/{id}/stream`|SSE stream for real-time updates|

#### 4.2.4 Sudo Provisioning

|Method|Endpoint              |Description                       |
|------|----------------------|----------------------------------|
|GET   |`/provisions`         |List all provisions with filters  |
|POST  |`/provisions`         |Create new sudo provision         |
|GET   |`/provisions/{id}`    |Get provision details             |
|PUT   |`/provisions/{id}`    |Update provision                  |
|DELETE|`/provisions/{id}`    |Revoke provision                  |
|POST  |`/provisions/jit`     |Create just-in-time access        |
|POST  |`/provisions/bulk`    |Bulk provision to multiple servers|
|GET   |`/provisions/expiring`|Get provisions expiring soon      |

#### 4.2.5 Log Search and Analysis

|Method|Endpoint                |Description                  |
|------|------------------------|-----------------------------|
|GET   |`/logs`                 |Search sudo logs with filters|
|GET   |`/logs/stats`           |Aggregated statistics        |
|GET   |`/logs/timeline`        |Time-series log data         |
|GET   |`/logs/export`          |Export logs (CSV/JSON)       |
|GET   |`/logs/users/{username}`|All logs for a user          |
|GET   |`/logs/commands/top`    |Most frequent commands       |

#### 4.2.6 Reports

|Method|Endpoint            |Description                |
|------|--------------------|---------------------------|
|GET   |`/reports`          |List saved reports         |
|POST  |`/reports`          |Generate new report        |
|GET   |`/reports/{id}`     |Get report details/download|
|GET   |`/reports/templates`|Available report templates |
|POST  |`/reports/schedule` |Schedule recurring report  |

### 4.3 Detailed Endpoint Specifications

#### POST `/api/v1/scan/single`

Initiate a sudo log scan on a single server.

**Request Body:**

```json
{
  "hostname": "server1.example.com",
  "options": {
    "log_sources": ["auth.log", "secure", "sudo.log"],
    "time_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-31T23:59:59Z"
    },
    "include_denied": true
  }
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Scan job queued successfully",
  "status_url": "/api/v1/scan/jobs/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "/api/v1/scan/jobs/550e8400-e29b-41d4-a716-446655440000/stream"
}
```

#### POST `/api/v1/scan/group`

Scan all servers in a group with parallel execution.

**Request Body:**

```json
{
  "group_id": 5,
  "thread_count": 50,
  "options": {
    "log_sources": ["auth.log", "secure"],
    "time_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": null
    },
    "timeout_per_host": 30,
    "continue_on_error": true
  }
}
```

#### POST `/api/v1/scan/file`

Scan servers from an uploaded file.

**Request (multipart/form-data):**

- `file`: Text file with one hostname per line
- `thread_count`: Number of parallel connections (1-200)
- `options`: JSON string with scan options

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "total_hosts": 1500,
  "thread_count": 100,
  "estimated_duration_seconds": 450
}
```

#### POST `/api/v1/provisions`

Create a new sudo provision.

**Request Body:**

```json
{
  "servers": [1, 2, 3],
  "principal_type": "group",
  "principal_name": "DOMAIN\\linux-admins",
  "sudo_rule": "ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart httpd, /usr/bin/journalctl",
  "is_jit": false,
  "grant_start": "2024-02-01T00:00:00Z",
  "grant_end": "2024-02-28T23:59:59Z",
  "justification": "Monthly maintenance window access",
  "ticket_reference": "CHG0012345"
}
```

**Response (201 Created):**

```json
{
  "provisions": [
    {
      "id": 101,
      "server_id": 1,
      "principal_type": "group",
      "principal_name": "DOMAIN\\linux-admins",
      "status": "pending",
      "deployment_job_id": "550e8400-e29b-41d4-a716-446655440002"
    }
  ],
  "deployment_job_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

#### POST `/api/v1/provisions/jit`

Create just-in-time sudo access.

**Request Body:**

```json
{
  "server_id": 42,
  "principal_type": "user",
  "principal_name": "jsmith",
  "sudo_rule": "ALL=(ALL) ALL",
  "duration_minutes": 60,
  "justification": "Emergency production issue - INC0098765",
  "auto_expire": true,
  "notify_on_use": true
}
```

#### GET `/api/v1/logs`

Search and filter sudo logs.

**Query Parameters:**

|Parameter   |Type    |Description                    |
|------------|--------|-------------------------------|
|`q`         |string  |Full-text search query         |
|`username`  |string  |Filter by username             |
|`hostname`  |string  |Filter by hostname             |
|`server_id` |integer |Filter by server ID            |
|`result`    |string  |“ACCEPT” or “DENY”             |
|`start_time`|datetime|Start of time range            |
|`end_time`  |datetime|End of time range              |
|`page`      |integer |Page number (default: 1)       |
|`page_size` |integer |Results per page (default: 50) |
|`sort`      |string  |Sort field (default: timestamp)|
|`order`     |string  |“asc” or “desc” (default: desc)|

**Response:**

```json
{
  "total": 15234,
  "page": 1,
  "page_size": 50,
  "pages": 305,
  "results": [
    {
      "id": 98765,
      "server": {
        "id": 1,
        "hostname": "webserver01",
        "fqdn": "webserver01.example.com"
      },
      "timestamp": "2024-01-15T14:32:18Z",
      "username": "jsmith",
      "tty": "pts/0",
      "pwd": "/home/jsmith",
      "runas_user": "root",
      "command": "/usr/bin/systemctl restart nginx",
      "result": "ACCEPT",
      "raw_log": "Jan 15 14:32:18 webserver01 sudo: jsmith : TTY=pts/0 ; PWD=/home/jsmith ; USER=root ; COMMAND=/usr/bin/systemctl restart nginx"
    }
  ]
}
```

#### GET `/api/v1/logs/export`

Export logs in CSV or JSON format.

**Query Parameters:**

- Same filters as `/logs` endpoint
- `format`: “csv” or “json” (default: json)
- `include_raw`: boolean (default: false)

**Response Headers:**

```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="sudo_logs_2024-01-15.csv"
```

-----

## 5. SSH Connection Management

### 5.1 Connection Pool Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SSH Connection Manager                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    Connection Pool Controller                     │   │
│   │  • Max connections configurable (default: 200)                   │   │
│   │  • Per-host connection limit (default: 3)                        │   │
│   │  • Connection timeout handling                                    │   │
│   │  • Health monitoring and auto-reconnect                          │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                │                                         │
│         ┌──────────────────────┼──────────────────────┐                 │
│         ▼                      ▼                      ▼                 │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐        │
│   │ ControlMaster │     │ ControlMaster │     │ ControlMaster │        │
│   │   Socket 1    │     │   Socket 2    │     │   Socket N    │        │
│   │  (server1)    │     │  (server2)    │     │  (serverN)    │        │
│   └───────┬───────┘     └───────┬───────┘     └───────┬───────┘        │
│           │                     │                     │                 │
│     ┌─────┴─────┐         ┌─────┴─────┐         ┌─────┴─────┐          │
│     ▼     ▼     ▼         ▼     ▼     ▼         ▼     ▼     ▼          │
│   [Mux] [Mux] [Mux]     [Mux] [Mux] [Mux]     [Mux] [Mux] [Mux]       │
│                                                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 SSH Configuration

The application will create and manage SSH configurations for optimal performance:

```
# /home/sudorecon/.ssh/config (managed by application)
Host *
    ControlMaster auto
    ControlPath /var/run/sudorecon/ssh-%r@%h:%p
    ControlPersist 600
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ConnectTimeout 10
    StrictHostKeyChecking accept-new
    UserKnownHostsFile /var/lib/sudorecon/known_hosts
    BatchMode yes
    LogLevel ERROR
```

### 5.3 Parallel Execution Strategy

```python
# Conceptual implementation
class SSHPoolManager:
    """
    Manages a pool of SSH connections with multiplexing support.
    
    Features:
    - Automatic ControlMaster socket management
    - Configurable concurrency limits
    - Connection health monitoring
    - Graceful degradation on failures
    """
    
    def __init__(self, max_concurrent: int = 100, timeout: int = 30):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout
        self.control_sockets = {}
        
    async def execute_on_hosts(
        self,
        hosts: List[str],
        command: str,
        callback: Callable
    ) -> Dict[str, Any]:
        """Execute command on multiple hosts concurrently."""
        tasks = [
            self._execute_with_limit(host, command, callback)
            for host in hosts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return dict(zip(hosts, results))
        
    async def _execute_with_limit(
        self,
        host: str,
        command: str,
        callback: Callable
    ) -> Any:
        """Execute with semaphore-based concurrency control."""
        async with self.semaphore:
            return await self._execute_ssh(host, command, callback)
```

### 5.4 Connection States and Monitoring

|State         |Description                      |Action                |
|--------------|---------------------------------|----------------------|
|`IDLE`        |Socket exists, no active sessions|Ready for new commands|
|`ACTIVE`      |Currently executing command(s)   |Monitor for completion|
|`ESTABLISHING`|Initial connection in progress   |Wait or timeout       |
|`FAILED`      |Connection failed                |Retry with backoff    |
|`STALE`       |Socket exists but unresponsive   |Close and recreate    |

-----

## 6. CLI Specification

### 6.1 Command Structure

```
sudorecon [OPTIONS] COMMAND [ARGS]...

Options:
  --api-url TEXT      API base URL (default: http://localhost:8080)
  --api-key TEXT      API key for authentication
  --config PATH       Path to config file
  --output FORMAT     Output format: table, json, csv (default: table)
  --quiet             Suppress non-essential output
  --verbose           Enable verbose logging
  --version           Show version and exit
  --help              Show this message and exit

Commands:
  scan        Scan servers for sudo logs
  provision   Manage sudo provisions
  logs        Search and export sudo logs
  servers     Manage server inventory
  groups      Manage server groups
  reports     Generate and manage reports
  config      Manage CLI configuration
```

### 6.2 Command Examples

#### Scanning Commands

```bash
# Scan a single server
sudorecon scan single webserver01.example.com

# Scan a single server with options
sudorecon scan single webserver01.example.com \
  --since "2024-01-01" \
  --until "2024-01-31" \
  --include-denied

# Scan a group of servers
sudorecon scan group production-web --threads 50

# Scan from a file with progress display
sudorecon scan file /path/to/servers.txt \
  --threads 100 \
  --timeout 60 \
  --continue-on-error \
  --progress

# Watch scan progress in real-time
sudorecon scan watch 550e8400-e29b-41d4-a716-446655440000
```

#### Provisioning Commands

```bash
# Grant sudo to a user on a single server
sudorecon provision grant \
  --server webserver01.example.com \
  --user jsmith \
  --rule "ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx" \
  --expires "2024-02-28" \
  --justification "Monthly maintenance"

# Grant sudo to an AD group on multiple servers
sudorecon provision grant \
  --group production-web \
  --ad-group "DOMAIN\\linux-admins" \
  --rule "ALL=(ALL) NOPASSWD: ALL" \
  --ticket CHG0012345

# Create JIT access
sudorecon provision jit \
  --server dbserver01.example.com \
  --user emergencyuser \
  --duration 60 \
  --notify ops@example.com

# List active provisions
sudorecon provision list --status active --expiring-within 7d

# Revoke a provision
sudorecon provision revoke 101 --reason "Access no longer needed"

# Bulk revoke by user
sudorecon provision revoke-user jsmith --all-servers
```

#### Log Commands

```bash
# Search logs
sudorecon logs search "systemctl restart" --since "7 days ago"

# Search by user across all servers
sudorecon logs search --user jsmith --limit 100

# Search by host
sudorecon logs search --host "web*" --result DENY

# Export logs to CSV
sudorecon logs export \
  --since "2024-01-01" \
  --until "2024-01-31" \
  --format csv \
  --output /tmp/sudo_logs.csv

# Show log statistics
sudorecon logs stats --group production-web --since "30 days ago"

# Real-time log tail (requires websocket support)
sudorecon logs tail --server webserver01.example.com
```

#### Server Management

```bash
# List servers
sudorecon servers list --status active

# Add a server
sudorecon servers add webserver05.example.com

# Add multiple servers from file
sudorecon servers import /path/to/new_servers.txt

# Remove a server
sudorecon servers remove webserver05.example.com

# Check server connectivity
sudorecon servers ping production-web --threads 20
```

### 6.3 CLI Output Formats

**Table Format (default):**

```
$ sudorecon logs search --user jsmith --limit 3

┌────────────────────────┬───────────────────┬────────┬─────────────────────────────────────┐
│ Timestamp              │ Server            │ Result │ Command                             │
├────────────────────────┼───────────────────┼────────┼─────────────────────────────────────┤
│ 2024-01-15 14:32:18    │ webserver01       │ ACCEPT │ /usr/bin/systemctl restart nginx    │
│ 2024-01-15 13:45:02    │ dbserver01        │ ACCEPT │ /usr/bin/psql -U postgres           │
│ 2024-01-15 11:22:45    │ webserver02       │ DENY   │ /usr/bin/rm -rf /var/log/*          │
└────────────────────────┴───────────────────┴────────┴─────────────────────────────────────┘

Showing 3 of 1,247 results
```

**JSON Format:**

```bash
$ sudorecon logs search --user jsmith --limit 1 --output json
```

```json
{
  "total": 1247,
  "results": [
    {
      "id": 98765,
      "timestamp": "2024-01-15T14:32:18Z",
      "server": "webserver01.example.com",
      "username": "jsmith",
      "command": "/usr/bin/systemctl restart nginx",
      "result": "ACCEPT"
    }
  ]
}
```

-----

## 7. Web Frontend Specification

### 7.1 Design System

#### Color Palette

|Name                |Hex      |Usage                          |
|--------------------|---------|-------------------------------|
|Background Primary  |`#0a0a0a`|Main app background            |
|Background Secondary|`#121212`|Cards, panels                  |
|Background Tertiary |`#1a1a1a`|Hover states, nested elements  |
|Border              |`#2a2a2a`|Dividers, card borders         |
|Terminal Green      |`#00ff41`|Primary text in terminal panels|
|Terminal Green Dim  |`#00cc34`|Secondary terminal text        |
|Accent Cyan         |`#00d4ff`|Interactive elements, links    |
|Success             |`#00ff88`|Success states                 |
|Warning             |`#ffaa00`|Warning states                 |
|Error               |`#ff4444`|Error states                   |
|Text Primary        |`#e0e0e0`|Primary text                   |
|Text Secondary      |`#888888`|Secondary text                 |

#### Typography

|Element      |Font                         |Size   |Weight|
|-------------|-----------------------------|-------|------|
|Terminal/Code|`JetBrains Mono`, `Fira Code`|13px   |400   |
|Headers      |`Inter`, `SF Pro Display`    |14-24px|600   |
|Body         |`Inter`, `SF Pro Text`       |14px   |400   |
|Labels       |`Inter`                      |12px   |500   |

### 7.2 Page Layouts

#### Dashboard (Landing Page)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │  SUDORECON                               🔍 Search ID, Host, or Log...    │ │
│  │  ══════════                              [________________________] [⚙️]  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│  │   ACTIVE HOSTS  │ │  ACTIVE GRANTS  │ │  LOGS (24H)     │ │  DENIED (24H) │ │
│  │  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │ │ ┌───────────┐ │ │
│  │  │   1,247   │  │ │  │     89    │  │ │  │  45,892   │  │ │ │    127    │ │ │
│  │  │  ▲ +12    │  │ │  │   ▲ +3    │  │ │  │   ▲ +5%   │  │ │ │   ▼ -8%  │ │ │
│  │  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │ │ └───────────┘ │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ └───────────────┘ │
│                                                                                  │
│  ┌──────────────────────────────────────────┐ ┌────────────────────────────────┐│
│  │  RECENT ACTIVITY                    [>]  │ │  EXPIRING SOON           [>]  ││
│  │  ════════════════                        │ │  ═════════════                 ││
│  │  ┌────────────────────────────────────┐  │ │  ┌──────────────────────────┐  ││
│  │  │ > jsmith@webserver01              │  │ │  │  DOMAIN\ops-team         │  ││
│  │  │   systemctl restart nginx         │  │ │  │  prod-cluster (12 hosts) │  ││
│  │  │   ACCEPT  2024-01-15 14:32:18     │  │ │  │  Expires: 2h 34m         │  ││
│  │  ├────────────────────────────────────┤  │ │  ├──────────────────────────┤  ││
│  │  │ > dbadmin@dbserver01              │  │ │  │  jsmith                  │  ││
│  │  │   psql -U postgres                │  │ │  │  webserver01             │  ││
│  │  │   ACCEPT  2024-01-15 14:30:45     │  │ │  │  Expires: 5h 12m         │  ││
│  │  ├────────────────────────────────────┤  │ │  └──────────────────────────┘  ││
│  │  │ > unknown@webserver02             │  │ │                                 ││
│  │  │   rm -rf /var/log/*               │  │ │  [View All Expiring Grants]     ││
│  │  │   ██DENY██  2024-01-15 14:28:12   │  │ │                                 ││
│  │  └────────────────────────────────────┘  │ └────────────────────────────────┘│
│  └──────────────────────────────────────────┘                                   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────┤
│  │  SUDO ACTIVITY (7 DAYS)                                                     │
│  │  ═══════════════════════                                                    │
│  │                                                                              │
│  │  2500 ┤                                    ╭─╮                              │
│  │       │                              ╭────╯  ╰╮                             │
│  │  2000 ┤                        ╭────╯         ╰╮                            │
│  │       │              ╭────────╯                ╰╮                           │
│  │  1500 ┤      ╭──────╯                           ╰────╮                      │
│  │       │╭────╯                                         ╰──╮                  │
│  │  1000 ┼╯                                                  ╰─────            │
│  │       └──────────────────────────────────────────────────────────           │
│  │         Mon    Tue    Wed    Thu    Fri    Sat    Sun    Mon                │
│  │                                                                              │
│  │  ── ACCEPT  ── DENY                                                         │
│  └──────────────────────────────────────────────────────────────────────────────┘
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Log Search View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SUDO LOG SEARCH                                                    [Export ▾] │
│  ═══════════════                                                               │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ 🔍 [systemctl restart________________]  [All Servers ▾] [All Users ▾]      ││
│  │                                                                              ││
│  │    📅 From: [2024-01-01    ] To: [2024-01-31    ]  ○ Accept ○ Deny ● All   ││
│  │                                                                              ││
│  │    [Search]  [Clear]                                         1,247 results  ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ ┌─────────────────────────────────────────────────────────────────────────┐ ││
│  │ │ TIMESTAMP            SERVER              USER       RESULT  COMMAND     │ ││
│  │ ├─────────────────────────────────────────────────────────────────────────┤ ││
│  │ │ 2024-01-15 14:32:18  webserver01         jsmith     ████    systemctl...│ ││
│  │ │ 2024-01-15 14:30:45  dbserver01          dbadmin    ████    psql -U p...│ ││
│  │ │ 2024-01-15 14:28:12  webserver02         unknown    ▓▓▓▓    rm -rf /v...│ ││
│  │ │ 2024-01-15 14:25:33  appserver01         deploy     ████    docker-co...│ ││
│  │ │ 2024-01-15 14:22:18  webserver01         jsmith     ████    systemctl...│ ││
│  │ └─────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                              ││
│  │  [< Prev]  Page 1 of 250  [Next >]                                          ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  LOG DETAIL                                                          [×]   ││
│  │  ══════════                                                                 ││
│  │  ╔══════════════════════════════════════════════════════════════════════╗  ││
│  │  ║ Jan 15 14:32:18 webserver01 sudo: jsmith : TTY=pts/0 ;              ║  ││
│  │  ║ PWD=/home/jsmith ; USER=root ; COMMAND=/usr/bin/systemctl restart   ║  ││
│  │  ║ nginx                                                                ║  ││
│  │  ╚══════════════════════════════════════════════════════════════════════╝  ││
│  │                                                                              ││
│  │  Server:    webserver01.example.com              Result:  ACCEPT            ││
│  │  User:      jsmith                               Run As:  root              ││
│  │  TTY:       pts/0                                PWD:     /home/jsmith      ││
│  │  Command:   /usr/bin/systemctl restart nginx                                ││
│  │                                                                              ││
│  │  [View User History]  [View Server Logs]  [Copy Raw Log]                    ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Scan Progress View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SCAN IN PROGRESS                                                              │
│  ════════════════                                                              │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  Job ID:     550e8400-e29b-41d4-a716-446655440000                          ││
│  │  Target:     production-web (1,500 hosts)                                   ││
│  │  Started:    2024-01-15 14:30:00                                            ││
│  │  Threads:    ████████████████████░░░░░░░░░░░░░░░░░░░░  50/100              ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  PROGRESS                                                                   ││
│  │  ════════                                                                   ││
│  │                                                                              ││
│  │  ████████████████████████████████░░░░░░░░░░░░░░░░  847/1500 (56%)          ││
│  │                                                                              ││
│  │  ✓ Completed: 832    ⚠ Failed: 15    ○ Pending: 653                        ││
│  │                                                                              ││
│  │  ETA: ~12 minutes remaining                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌────────────────────────────────────┐ ┌──────────────────────────────────────┐│
│  │  LIVE OUTPUT                  [>]  │ │  FAILED HOSTS                   [>] ││
│  │  ═══════════                       │ │  ════════════                        ││
│  │  ╔════════════════════════════════╗│ │  ┌────────────────────────────────┐  ││
│  │  ║ > Scanning webserver847...    ║│ │  │ dbserver12     Connection timeout││
│  │  ║ > Parsing 2,341 log entries   ║│ │  │ appserver22    Permission denied ││
│  │  ║ > Completed webserver846      ║│ │  │ webserver99    Host unreachable  ││
│  │  ║ > Scanning webserver848...    ║│ │  │ loadbalancer3  SSH key rejected  ││
│  │  ║ > Completed webserver845      ║│ │  │ cache01        Connection refused││
│  │  ║ > Parsing 1,892 log entries   ║│ │  └────────────────────────────────┘  ││
│  │  ║ > Scanning webserver849...    ║│ │                                       ││
│  │  ╚════════════════════════════════╝│ │  [Retry Failed]  [Export List]       ││
│  └────────────────────────────────────┘ └──────────────────────────────────────┘│
│                                                                                  │
│  [Cancel Scan]                                         [View Results When Done] │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Provision Management View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SUDO PROVISIONS                                              [+ New Provision] │
│  ═══════════════                                                                │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  Filter: [All Statuses ▾] [All Servers ▾] [All Principals ▾]  🔍 [Search_] ││
│  │                                                                              ││
│  │  ☐ Show JIT Only    ☐ Show Expiring (< 24h)                                 ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ ┌─────────────────────────────────────────────────────────────────────────┐ ││
│  │ │ STATUS    PRINCIPAL              SERVERS     RULE              EXPIRES  │ ││
│  │ ├─────────────────────────────────────────────────────────────────────────┤ ││
│  │ │ ●ACTIVE   DOMAIN\linux-admins    12 hosts    ALL=(ALL) ALL     28d      │ ││
│  │ │ ●ACTIVE   jsmith (user)          3 hosts     systemctl only    2h 34m   │ ││
│  │ │ ●PENDING  DOMAIN\ops-team        8 hosts     docker-compose    awaiting │ ││
│  │ │ ○EXPIRED  contractor1 (user)     1 host      ALL=(ALL) ALL     -5d      │ ││
│  │ │ ⊘REVOKED  DOMAIN\dev-team        24 hosts    yum/dnf only      revoked  │ ││
│  │ └─────────────────────────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  NEW PROVISION                                                        [×]  ││
│  │  ═════════════                                                              ││
│  │                                                                              ││
│  │  Target Servers                                                             ││
│  │  ○ Single Server  [webserver01.example.com        ]                        ││
│  │  ● Server Group   [production-web               ▾]                         ││
│  │  ○ Upload File    [Choose File...]                                          ││
│  │                                                                              ││
│  │  Principal                                                                   ││
│  │  ● User    [jsmith                              ]                           ││
│  │  ○ AD Group [DOMAIN\____________________________]                           ││
│  │                                                                              ││
│  │  Sudo Rule                                                                   ││
│  │  ┌────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx                   │ ││
│  │  └────────────────────────────────────────────────────────────────────────┘ ││
│  │  [Common Rules ▾]  [Validate Syntax]                                        ││
│  │                                                                              ││
│  │  Access Window                                                               ││
│  │  ● Time-Limited    From: [2024-02-01 00:00]  To: [2024-02-28 23:59]        ││
│  │  ○ JIT (Duration)  [60] minutes                                             ││
│  │  ○ Permanent (requires approval)                                            ││
│  │                                                                              ││
│  │  Thread Count: ━━━━━━━━━━━━●━━━━━━━━━  50                                  ││
│  │                1          50         200                                    ││
│  │                                                                              ││
│  │  Justification                                                               ││
│  │  ┌────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ Monthly maintenance window for nginx configuration updates             │ ││
│  │  └────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                              ││
│  │  Ticket Reference: [CHG0012345         ]  (optional)                        ││
│  │                                                                              ││
│  │  [Cancel]                                              [Deploy Provision]   ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Component Hierarchy

```
App
├── Layout
│   ├── Sidebar
│   │   ├── Logo
│   │   ├── NavItem (Dashboard)
│   │   ├── NavItem (Scan)
│   │   ├── NavItem (Provisions)
│   │   ├── NavItem (Logs)
│   │   ├── NavItem (Reports)
│   │   ├── NavItem (Servers)
│   │   └── UserMenu
│   ├── TopBar
│   │   ├── GlobalSearch
│   │   ├── NotificationBell
│   │   └── SettingsGear
│   └── MainContent
│       └── [Page Components]
│
├── Pages
│   ├── Dashboard
│   │   ├── StatsCards
│   │   ├── RecentActivityFeed
│   │   ├── ExpiringProvisions
│   │   └── ActivityChart
│   ├── Scan
│   │   ├── ScanForm
│   │   │   ├── TargetSelector
│   │   │   ├── ThreadSlider
│   │   │   └── OptionsPanel
│   │   ├── JobList
│   │   └── JobProgress
│   │       ├── ProgressBar
│   │       ├── LiveOutput (Terminal)
│   │       └── FailedHostsList
│   ├── Provisions
│   │   ├── ProvisionFilters
│   │   ├── ProvisionTable
│   │   ├── ProvisionDetail
│   │   └── NewProvisionModal
│   ├── Logs
│   │   ├── SearchForm
│   │   ├── LogTable
│   │   ├── LogDetail (Terminal)
│   │   └── ExportDialog
│   ├── Reports
│   │   ├── ReportTemplates
│   │   ├── ReportGenerator
│   │   ├── ReportList
│   │   └── ReportViewer
│   └── Servers
│       ├── ServerList
│       ├── ServerDetail
│       ├── GroupManager
│       └── ImportServers
│
└── Shared Components
    ├── Terminal (green-on-black display)
    ├── DataTable (sortable, filterable)
    ├── Pagination
    ├── Modal
    ├── Tooltip
    ├── Badge (status indicators)
    ├── Button (variants)
    ├── Input (text, select, date)
    ├── Slider
    ├── ProgressBar
    ├── Chart (line, bar)
    └── Toast (notifications)
```

### 7.4 Terminal Component Specification

The terminal component provides the distinctive “system” aesthetic for log displays and live output.

```jsx
// TerminalDisplay.tsx - Conceptual implementation
interface TerminalDisplayProps {
  content: string | string[];
  title?: string;
  maxHeight?: string;
  autoScroll?: boolean;
  showLineNumbers?: boolean;
  highlightPatterns?: HighlightRule[];
  onCopy?: () => void;
}

// Highlight rules for log parsing
const defaultHighlightRules: HighlightRule[] = [
  { pattern: /ACCEPT/g, className: 'text-success' },
  { pattern: /DENY/g, className: 'text-error bg-error/20' },
  { pattern: /sudo:/g, className: 'text-cyan' },
  { pattern: /\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/g, className: 'text-dim' },
  { pattern: /COMMAND=.*/g, className: 'text-green-bright' },
];
```

**Terminal CSS:**

```css
.terminal-container {
  background: #000000;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 16px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow: auto;
}

.terminal-text {
  color: #00ff41;
  text-shadow: 0 0 2px #00ff41;
}

.terminal-text-dim {
  color: #00cc34;
}

.terminal-text-error {
  color: #ff4444;
  background: rgba(255, 68, 68, 0.15);
  padding: 0 4px;
}

.terminal-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}
```

-----

## 8. Project Structure

```
sudorecon/
├── README.md
├── LICENSE
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── alembic.ini
│
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Configuration management
│   ├── dependencies.py            # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # API router aggregation
│   │   │   ├── servers.py         # Server endpoints
│   │   │   ├── groups.py          # Group endpoints
│   │   │   ├── scan.py            # Scan endpoints
│   │   │   ├── provisions.py      # Provision endpoints
│   │   │   ├── logs.py            # Log endpoints
│   │   │   ├── reports.py         # Report endpoints
│   │   │   └── auth.py            # Authentication endpoints
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py            # Auth middleware
│   │       ├── logging.py         # Request logging
│   │       └── rate_limit.py      # Rate limiting
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy base
│   │   ├── server.py              # Server models
│   │   ├── provision.py           # Provision models
│   │   ├── log.py                 # Log models
│   │   ├── job.py                 # Job models
│   │   └── user.py                # User models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── server.py              # Server Pydantic schemas
│   │   ├── provision.py           # Provision schemas
│   │   ├── log.py                 # Log schemas
│   │   ├── job.py                 # Job schemas
│   │   └── common.py              # Shared schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── server_service.py      # Server business logic
│   │   ├── provision_service.py   # Provision business logic
│   │   ├── log_service.py         # Log business logic
│   │   ├── scan_service.py        # Scan orchestration
│   │   └── report_service.py      # Report generation
│   │
│   ├── ssh/
│   │   ├── __init__.py
│   │   ├── pool.py                # SSH connection pool
│   │   ├── executor.py            # Command execution
│   │   ├── multiplexer.py         # ControlMaster management
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── auth_log.py        # auth.log parser
│   │       ├── secure.py          # secure log parser
│   │       └── sudo_log.py        # sudo.log parser
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery configuration
│   │   ├── scan_tasks.py          # Scan background tasks
│   │   ├── provision_tasks.py     # Provision background tasks
│   │   └── maintenance_tasks.py   # Cleanup, expiry tasks
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py             # Database session
│   │   └── migrations/            # Alembic migrations
│   │       ├── env.py
│   │       └── versions/
│   │
│   └── utils/
│       ├── __init__.py
│       ├── sudoers.py             # Sudoers file manipulation
│       ├── ad_utils.py            # AD/QAS utilities
│       └── export.py              # CSV/JSON export utilities
│
├── cli/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── scan.py                # Scan commands
│   │   ├── provision.py           # Provision commands
│   │   ├── logs.py                # Log commands
│   │   ├── servers.py             # Server commands
│   │   └── config.py              # Config commands
│   └── utils/
│       ├── __init__.py
│       ├── output.py              # Output formatting
│       └── progress.py            # Progress display
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   ├── src/
│   │   ├── main.tsx               # React entry
│   │   ├── App.tsx                # Root component
│   │   ├── index.css              # Global styles
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts          # API client setup
│   │   │   ├── servers.ts         # Server API calls
│   │   │   ├── provisions.ts      # Provision API calls
│   │   │   ├── logs.ts            # Log API calls
│   │   │   └── scan.ts            # Scan API calls
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── TopBar.tsx
│   │   │   │   └── MainLayout.tsx
│   │   │   ├── common/
│   │   │   │   ├── Terminal.tsx
│   │   │   │   ├── DataTable.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Slider.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   └── ProgressBar.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── StatsCard.tsx
│   │   │   │   ├── ActivityFeed.tsx
│   │   │   │   └── ActivityChart.tsx
│   │   │   ├── scan/
│   │   │   │   ├── ScanForm.tsx
│   │   │   │   ├── JobProgress.tsx
│   │   │   │   └── LiveOutput.tsx
│   │   │   ├── provisions/
│   │   │   │   ├── ProvisionTable.tsx
│   │   │   │   ├── ProvisionForm.tsx
│   │   │   │   └── ProvisionDetail.tsx
│   │   │   └── logs/
│   │   │       ├── LogSearch.tsx
│   │   │       ├── LogTable.tsx
│   │   │       └── LogDetail.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Scan.tsx
│   │   │   ├── Provisions.tsx
│   │   │   ├── Logs.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── Servers.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useApi.ts
│   │   │   ├── useSSE.ts          # Server-sent events
│   │   │   └── useWebSocket.ts
│   │   │
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   └── uiStore.ts
│   │   │
│   │   └── types/
│   │       ├── server.ts
│   │       ├── provision.ts
│   │       ├── log.ts
│   │       └── job.ts
│   │
│   └── tests/
│       └── ...
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_parsers.py
│   │   ├── test_ssh_pool.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_tasks.py
│   └── e2e/
│       └── test_workflows.py
│
├── scripts/
│   ├── setup.sh                   # Initial setup script
│   ├── deploy.sh                  # Deployment script
│   └── backup.sh                  # Database backup
│
├── config/
│   ├── sudorecon.yaml.example     # Example config
│   ├── systemd/
│   │   ├── sudorecon-api.service
│   │   ├── sudorecon-worker.service
│   │   └── sudorecon-beat.service
│   └── nginx/
│       └── sudorecon.conf
│
└── docs/
    ├── installation.md
    ├── configuration.md
    ├── api.md
    ├── cli.md
    └── architecture.md
```

-----

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

|Task|Description           |Deliverables                         |
|----|----------------------|-------------------------------------|
|1.1 |Project scaffolding   |Repository structure, CI/CD setup    |
|1.2 |Database schema       |PostgreSQL schema, Alembic migrations|
|1.3 |Core API framework    |FastAPI setup, auth, basic CRUD      |
|1.4 |SSH connection manager|asyncssh integration, ControlMaster  |
|1.5 |Basic CLI             |Click framework, config management   |

### Phase 2: Core Features (Weeks 4-6)

|Task|Description         |Deliverables                                    |
|----|--------------------|------------------------------------------------|
|2.1 |Log parsing engine  |Multi-format parser (auth.log, secure, sudo.log)|
|2.2 |Single-host scanning|Complete scan workflow for one host             |
|2.3 |Parallel scanning   |Celery tasks, connection pooling                |
|2.4 |Log search API      |Full-text search, filtering, pagination         |
|2.5 |Basic web UI        |React app, dashboard, log viewer                |

### Phase 3: Provisioning (Weeks 7-9)

|Task|Description         |Deliverables                       |
|----|--------------------|-----------------------------------|
|3.1 |Sudoers manipulation|Safe sudoers file editing          |
|3.2 |Provision API       |Create, read, revoke provisions    |
|3.3 |AD/QAS integration  |Domain group resolution, validation|
|3.4 |JIT access          |Time-limited grants, auto-expiry   |
|3.5 |Bulk provisioning   |Multi-server parallel deployment   |

### Phase 4: Advanced Features (Weeks 10-12)

|Task|Description         |Deliverables                          |
|----|--------------------|--------------------------------------|
|4.1 |Real-time updates   |SSE/WebSocket for live progress       |
|4.2 |Reporting engine    |Templates, scheduled reports          |
|4.3 |Export functionality|CSV/JSON export                       |
|4.4 |Audit logging       |Complete action history               |
|4.5 |UI polish           |Terminal aesthetics, responsive design|

### Phase 5: Hardening (Weeks 13-14)

|Task|Description           |Deliverables                   |
|----|----------------------|-------------------------------|
|5.1 |Security review       |Penetration testing, code audit|
|5.2 |Performance tuning    |Query optimization, caching    |
|5.3 |Documentation         |User guides, API docs          |
|5.4 |Deployment automation |Ansible/Docker deployment      |
|5.5 |Monitoring integration|Prometheus metrics, alerts     |

-----

## 10. Security Considerations

### 10.1 Authentication & Authorization

- API key authentication for programmatic access
- JWT tokens for web UI sessions
- Role-based access control (RBAC): Viewer, Operator, Admin, Superadmin
- AD/LDAP integration for SSO
- API key rotation and expiry

### 10.2 SSH Security

- Jump server runs with dedicated service account
- SSH keys rotated on schedule
- ControlMaster sockets in protected directory (`/var/run/sudorecon/`)
- Strict host key verification
- Connection audit logging

### 10.3 Data Protection

- TLS encryption for all API traffic
- Database encryption at rest
- Sensitive fields encrypted in database (API keys, etc.)
- Log data retention policies
- PII handling for audit compliance

### 10.4 Audit Trail

- All actions logged with user, timestamp, IP
- Immutable audit log table
- Provision history tracking
- API request/response logging (sanitized)

-----

## 11. Deployment Architecture

### 11.1 Recommended Production Setup

```
                        ┌─────────────────────────────┐
                        │        Load Balancer        │
                        │      (HAProxy/nginx)        │
                        └─────────────┬───────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │   API Node 1    │     │   API Node 2    │     │   API Node N    │
    │   (FastAPI)     │     │   (FastAPI)     │     │   (FastAPI)     │
    └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
             │                       │                       │
             └───────────────────────┼───────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────┐
         │                           │                       │
         ▼                           ▼                       ▼
┌─────────────────┐        ┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL    │        │     Redis       │      │  Celery Workers │
│   (Primary +    │        │   (Cluster)     │      │   (Scalable)    │
│    Replica)     │        │                 │      │                 │
└─────────────────┘        └─────────────────┘      └─────────────────┘
```

### 11.2 Docker Compose (Development)

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://sudorecon:secret@db:5432/sudorecon
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app/backend
      - ssh-sockets:/var/run/sudorecon
    depends_on:
      - db
      - redis

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://sudorecon:secret@db:5432/sudorecon
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ssh-sockets:/var/run/sudorecon
      - ssh-keys:/home/sudorecon/.ssh:ro
    depends_on:
      - db
      - redis

  beat:
    build:
      context: .
      dockerfile: Dockerfile.beat
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=sudorecon
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=sudorecon
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  postgres-data:
  redis-data:
  ssh-sockets:
  ssh-keys:
```

-----

## 12. Monitoring & Observability

### 12.1 Metrics (Prometheus)

|Metric                            |Type     |Description                    |
|----------------------------------|---------|-------------------------------|
|`sudorecon_scan_jobs_total`       |Counter  |Total scan jobs by status      |
|`sudorecon_scan_duration_seconds` |Histogram|Scan job duration              |
|`sudorecon_ssh_connections_active`|Gauge    |Active SSH connections         |
|`sudorecon_provisions_active`     |Gauge    |Active sudo provisions         |
|`sudorecon_logs_ingested_total`   |Counter  |Logs ingested per server       |
|`sudorecon_api_requests_total`    |Counter  |API requests by endpoint/status|
|`sudorecon_api_latency_seconds`   |Histogram|API response latency           |

### 12.2 Logging (Structured JSON)

```json
{
  "timestamp": "2024-01-15T14:32:18.123Z",
  "level": "INFO",
  "service": "sudorecon-api",
  "trace_id": "abc123",
  "span_id": "def456",
  "user": "jsmith",
  "action": "provision.create",
  "resource_type": "provision",
  "resource_id": "101",
  "message": "Created sudo provision",
  "details": {
    "servers": [1, 2, 3],
    "principal": "DOMAIN\\linux-admins",
    "expires": "2024-02-28T23:59:59Z"
  }
}
```

### 12.3 Health Checks

|Endpoint       |Check                               |
|---------------|------------------------------------|
|`/health`      |Basic liveness                      |
|`/health/ready`|Database, Redis, worker connectivity|
|`/health/ssh`  |SSH pool status                     |

-----

## 13. Future Enhancements

### 13.1 Potential Features

- **Approval Workflows**: Multi-level approval for sensitive provisions
- **SIEM Integration**: Direct log shipping to Splunk, ELK, etc.
- **Terraform Provider**: Infrastructure-as-code provisioning
- **Mobile App**: iOS/Android for emergency JIT access
- **AI/ML Analysis**: Anomaly detection in sudo patterns
- **SSO Integration**: SAML/OIDC for enterprise auth
- **Multi-tenant**: Support for multiple organizations
- **Offline Mode**: Queue changes when target unreachable

### 13.2 Scalability Roadmap

- Horizontal API scaling with stateless design
- Database read replicas for heavy query loads
- Elasticsearch integration for log search at scale
- Sharded log storage for multi-year retention
- Geo-distributed deployment for global enterprises

-----

## 14. Appendices

### Appendix A: Sudo Log Parsing Patterns

```python
# auth.log / secure log pattern
AUTH_LOG_PATTERN = re.compile(
    r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<hostname>\S+)\s+'
    r'sudo:\s+'
    r'(?P<username>\S+)\s+:\s+'
    r'(TTY=(?P<tty>\S+)\s+;\s+)?'
    r'PWD=(?P<pwd>[^;]+)\s*;\s+'
    r'USER=(?P<runas>\S+)\s*;\s+'
    r'COMMAND=(?P<command>.+)$'
)

# sudo.log pattern (dedicated sudo log)
SUDO_LOG_PATTERN = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<username>\S+)\s+:\s+'
    r'(?P<result>ACCEPT|DENY)\s+'
    r'(?P<command>.+)$'
)
```

### Appendix B: Sudoers Template Examples

```
# User-specific rule
{username} ALL=(ALL) NOPASSWD: {commands}

# AD Group rule (QAS/VAS format)
%{domain}\\{groupname} ALL=(ALL) NOPASSWD: {commands}

# Time-limited rule (with comment for tracking)
# SUDORECON_PROVISION_ID={id} EXPIRES={expiry}
{principal} ALL=(ALL) NOPASSWD: {commands}
```

### Appendix C: Configuration File Schema

```yaml
# /etc/sudorecon/config.yaml
app:
  name: SudoRecon
  version: 1.0.0
  debug: false
  log_level: INFO

database:
  url: postgresql://user:pass@localhost:5432/sudorecon
  pool_size: 20
  max_overflow: 10

redis:
  url: redis://localhost:6379/0
  
ssh:
  user: sudorecon
  key_path: /home/sudorecon/.ssh/id_rsa
  control_path: /var/run/sudorecon/ssh-%r@%h:%p
  control_persist: 600
  connect_timeout: 10
  max_connections: 200
  per_host_limit: 3

api:
  host: 0.0.0.0
  port: 8080
  workers: 4
  cors_origins:
    - http://localhost:3000
  rate_limit:
    requests: 100
    period: 60

celery:
  broker_url: redis://localhost:6379/1
  result_backend: redis://localhost:6379/2
  task_time_limit: 3600

security:
  jwt_secret: ${JWT_SECRET}
  jwt_expiry_hours: 24
  api_key_hash_algorithm: sha256
  allowed_domains:
    - example.com
```

-----

This document provides the complete technical specification for the SudoRecon application. Implementation should proceed according to the phased approach outlined in Section 9, with regular reviews and adjustments as development progresses.
