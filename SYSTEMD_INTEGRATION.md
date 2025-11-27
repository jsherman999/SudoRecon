# SudoRecon Systemd Integration & Administrative Tools for RHEL9

Complete guide for systemd integration, monitoring, and administrative tooling for production deployment.

## Table of Contents

- [Systemd Service Units](#systemd-service-units)
- [Service Management](#service-management)
- [Log Management](#log-management)
- [Administrative Tools](#administrative-tools)
- [Monitoring Scripts](#monitoring-scripts)
- [Cron Jobs](#cron-jobs)
- [Health Checks](#health-checks)
- [Troubleshooting Tools](#troubleshooting-tools)
- [Performance Monitoring](#performance-monitoring)

---

## Systemd Service Units

### Complete Service Definitions

#### 1. API Service

`/etc/systemd/system/sudorecon-api.service`

```ini
[Unit]
Description=SudoRecon API Service
Documentation=https://github.com/jsherman999/SudoRecon
After=network-online.target postgresql-15.service redis.service
Wants=network-online.target
Requires=postgresql-15.service redis.service

[Service]
Type=notify
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/sudorecon /var/run/sudorecon
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Main process
ExecStartPre=/opt/sudorecon/app/venv/bin/python -c "from backend.db.session import test_connection; test_connection()"
ExecStart=/opt/sudorecon/app/venv/bin/gunicorn \
    backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8080 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile /var/log/sudorecon/api-access.log \
    --error-logfile /var/log/sudorecon/api-error.log \
    --log-level info \
    --pid /var/run/sudorecon/api.pid

ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sudorecon-api

[Install]
WantedBy=multi-user.target
```

#### 2. Celery Worker Service

`/etc/systemd/system/sudorecon-worker.service`

```ini
[Unit]
Description=SudoRecon Celery Worker
Documentation=https://github.com/jsherman999/SudoRecon
After=network.target redis.service postgresql-15.service
Requires=redis.service postgresql-15.service

[Service]
Type=forking
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/sudorecon /var/run/sudorecon /opt/sudorecon/.ssh
ProtectKernelTunables=true
ProtectKernelModules=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Main process
ExecStart=/opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --logfile=/var/log/sudorecon/worker.log \
    --pidfile=/var/run/sudorecon/worker.pid \
    --detach

ExecStop=/bin/kill -TERM $MAINPID
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=60

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sudorecon-worker

[Install]
WantedBy=multi-user.target
```

#### 3. Celery Beat Service

`/etc/systemd/system/sudorecon-beat.service`

```ini
[Unit]
Description=SudoRecon Celery Beat Scheduler
Documentation=https://github.com/jsherman999/SudoRecon
After=network.target redis.service
Requires=redis.service
PartOf=sudorecon-worker.service

[Service]
Type=simple
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/sudorecon /var/run/sudorecon
ProtectKernelTunables=true

# Main process
ExecStart=/opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app beat \
    --loglevel=info \
    --logfile=/var/log/sudorecon/beat.log \
    --pidfile=/var/run/sudorecon/beat.pid \
    --schedule=/var/run/sudorecon/celerybeat-schedule

KillMode=mixed
TimeoutStopSec=30

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sudorecon-beat

[Install]
WantedBy=multi-user.target
```

#### 4. Service Target (All Services)

`/etc/systemd/system/sudorecon.target`

```ini
[Unit]
Description=SudoRecon Application Stack
Documentation=https://github.com/jsherman999/SudoRecon
Wants=postgresql-15.service redis.service
After=postgresql-15.service redis.service

[Install]
WantedBy=multi-user.target
```

---

## Service Management

### Installation

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.target /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable sudorecon-api
sudo systemctl enable sudorecon-worker
sudo systemctl enable sudorecon-beat
sudo systemctl enable sudorecon.target

# Start all services
sudo systemctl start sudorecon.target
```

### Common Operations

```bash
# Start all services
sudo systemctl start sudorecon-api sudorecon-worker sudorecon-beat

# Stop all services
sudo systemctl stop sudorecon-beat sudorecon-worker sudorecon-api

# Restart services
sudo systemctl restart sudorecon-api
sudo systemctl restart sudorecon-worker

# Reload API (graceful restart)
sudo systemctl reload sudorecon-api

# Check status
sudo systemctl status sudorecon-api
sudo systemctl status sudorecon-worker
sudo systemctl status sudorecon-beat

# View service logs
sudo journalctl -u sudorecon-api -f
sudo journalctl -u sudorecon-worker -f --since "1 hour ago"

# Check service dependencies
systemctl list-dependencies sudorecon-api
```

---

## Log Management

### Logrotate Configuration

`/etc/logrotate.d/sudorecon`

```
/var/log/sudorecon/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 sudorecon sudorecon
    sharedscripts
    postrotate
        systemctl reload sudorecon-api >/dev/null 2>&1 || true
        systemctl reload sudorecon-worker >/dev/null 2>&1 || true
    endscript
}

/var/log/sudorecon/api-access.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    missingok
    create 0640 sudorecon sudorecon
    size 100M
    postrotate
        systemctl reload sudorecon-api >/dev/null 2>&1 || true
    endscript
}
```

### Journald Configuration

`/etc/systemd/journald.conf.d/sudorecon.conf`

```ini
[Journal]
# Persistent storage
Storage=persistent
Compress=yes

# Retention
MaxRetentionSec=30day
MaxFileSec=1day

# Size limits
SystemMaxUse=2G
SystemKeepFree=500M
SystemMaxFileSize=100M

# Forward to syslog for external logging
ForwardToSyslog=no
ForwardToWall=no
```

---

## Administrative Tools

### 1. Service Management Script

`/usr/local/bin/sudorecon-service`

```bash
#!/bin/bash
#
# SudoRecon Service Management Script
# Usage: sudorecon-service {start|stop|restart|status|logs|health}
#

set -e

SERVICES=("sudorecon-api" "sudorecon-worker" "sudorecon-beat")
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_status() {
    local service=$1
    local status=$(systemctl is-active "$service" 2>/dev/null || echo "inactive")
    
    if [ "$status" = "active" ]; then
        echo -e "${GREEN}✓${NC} $service: ${GREEN}running${NC}"
    else
        echo -e "${RED}✗${NC} $service: ${RED}$status${NC}"
    fi
}

function check_health() {
    echo "Checking SudoRecon health..."
    echo
    
    # Check services
    echo "=== Services ==="
    for service in "${SERVICES[@]}"; do
        print_status "$service"
    done
    echo
    
    # Check database connection
    echo "=== Database ==="
    if sudo -u sudorecon psql -h localhost -U sudorecon sudorecon -c "SELECT 1;" &>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL: connected"
    else
        echo -e "${RED}✗${NC} PostgreSQL: connection failed"
    fi
    echo
    
    # Check Redis
    echo "=== Redis ==="
    if redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis: connected"
    else
        echo -e "${RED}✗${NC} Redis: connection failed"
    fi
    echo
    
    # Check API endpoint
    echo "=== API Health ==="
    if curl -sf http://localhost:8080/health &>/dev/null; then
        echo -e "${GREEN}✓${NC} API: responding"
    else
        echo -e "${RED}✗${NC} API: not responding"
    fi
    echo
    
    # Check disk space
    echo "=== Disk Space ==="
    df -h /var/log/sudorecon /opt/sudorecon | tail -n +2
    echo
    
    # Check process counts
    echo "=== Processes ==="
    echo "API workers: $(pgrep -fc 'gunicorn.*sudorecon')"
    echo "Celery workers: $(pgrep -fc 'celery.*worker')"
    echo
}

function show_logs() {
    local service=${1:-sudorecon-api}
    local lines=${2:-50}
    echo "Showing last $lines lines from $service..."
    sudo journalctl -u "$service" -n "$lines" --no-pager
}

case "${1:-}" in
    start)
        echo "Starting SudoRecon services..."
        for service in "${SERVICES[@]}"; do
            sudo systemctl start "$service"
            echo "Started $service"
        done
        ;;
    stop)
        echo "Stopping SudoRecon services..."
        for service in $(echo "${SERVICES[@]}" | tac -s ' '); do
            sudo systemctl stop "$service"
            echo "Stopped $service"
        done
        ;;
    restart)
        echo "Restarting SudoRecon services..."
        for service in $(echo "${SERVICES[@]}" | tac -s ' '); do
            sudo systemctl restart "$service"
            echo "Restarted $service"
        done
        ;;
    status)
        for service in "${SERVICES[@]}"; do
            print_status "$service"
        done
        ;;
    health)
        check_health
        ;;
    logs)
        show_logs "${2:-sudorecon-api}" "${3:-50}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service] [lines]|health}"
        exit 1
        ;;
esac
```

### 2. Database Maintenance Script

`/usr/local/bin/sudorecon-db-maint`

```bash
#!/bin/bash
#
# SudoRecon Database Maintenance
# Performs VACUUM, ANALYZE, and provides database statistics
#

set -e

DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-sudorecon}"
DB_USER="${DB_USER:-sudorecon}"
LOG_DIR="/var/log/sudorecon"
LOG_FILE="$LOG_DIR/db-maintenance.log"

function log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

function run_vacuum() {
    log_msg "Running VACUUM ANALYZE..."
    sudo -u postgres psql -h "$DB_HOST" "$DB_NAME" << 'EOF'
VACUUM (VERBOSE, ANALYZE);
EOF
    log_msg "VACUUM completed"
}

function show_stats() {
    log_msg "Database Statistics:"
    sudo -u postgres psql -h "$DB_HOST" "$DB_NAME" << 'EOF'
-- Database size
SELECT pg_size_pretty(pg_database_size('sudorecon')) AS database_size;

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup AS rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(schemaname||'.'||indexname) DESC
LIMIT 10;

-- Connection count
SELECT count(*) AS connections, state FROM pg_stat_activity 
WHERE datname = 'sudorecon' GROUP BY state;
EOF
}

function cleanup_old_data() {
    local days=${1:-90}
    log_msg "Cleaning up data older than $days days..."
    
    sudo -u sudorecon /opt/sudorecon/app/venv/bin/python << EOF
from backend.db.session import SessionLocal
from backend.models import ScanJob, SudoLog
from datetime import datetime, timedelta
from sqlalchemy import delete

db = SessionLocal()
try:
    cutoff = datetime.utcnow() - timedelta(days=$days)
    
    # Delete old completed scan jobs
    result = db.execute(
        delete(ScanJob).where(
            ScanJob.status == 'completed',
            ScanJob.completed_at < cutoff
        )
    )
    db.commit()
    print(f"Deleted {result.rowcount} old scan jobs")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
EOF
}

case "${1:-stats}" in
    vacuum)
        run_vacuum
        ;;
    stats)
        show_stats
        ;;
    cleanup)
        cleanup_old_data "${2:-90}"
        ;;
    all)
        run_vacuum
        show_stats
        cleanup_old_data 90
        ;;
    *)
        echo "Usage: $0 {vacuum|stats|cleanup [days]|all}"
        exit 1
        ;;
esac
```

### 3. Backup Script

`/usr/local/bin/sudorecon-backup`

```bash
#!/bin/bash
#
# SudoRecon Backup Script
# Backs up database and configuration files
#

set -e

BACKUP_DIR="/var/backups/sudorecon"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="sudorecon"
DB_USER="sudorecon"

# Create backup directory
mkdir -p "$BACKUP_DIR"

function backup_database() {
    echo "Backing up database..."
    local backup_file="$BACKUP_DIR/sudorecon_db_$TIMESTAMP.sql.gz"
    
    sudo -u postgres pg_dump "$DB_NAME" | gzip > "$backup_file"
    
    echo "Database backup created: $backup_file"
    echo "Size: $(du -h "$backup_file" | cut -f1)"
}

function backup_config() {
    echo "Backing up configuration..."
    local backup_file="$BACKUP_DIR/sudorecon_config_$TIMESTAMP.tar.gz"
    
    tar czf "$backup_file" \
        /etc/sudorecon \
        /opt/sudorecon/.ssh/known_hosts \
        /etc/systemd/system/sudorecon-*.service \
        2>/dev/null || true
    
    echo "Config backup created: $backup_file"
}

function backup_logs() {
    echo "Backing up recent logs..."
    local backup_file="$BACKUP_DIR/sudorecon_logs_$TIMESTAMP.tar.gz"
    
    find /var/log/sudorecon -name "*.log" -mtime -7 -exec \
        tar czf "$backup_file" {} + 2>/dev/null || true
    
    echo "Log backup created: $backup_file"
}

function cleanup_old_backups() {
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "sudorecon_*" -mtime "+$RETENTION_DAYS" -delete
    echo "Cleanup complete"
}

function list_backups() {
    echo "Available backups:"
    ls -lh "$BACKUP_DIR" | tail -n +2
}

function restore_database() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        echo "Error: Backup file not found: $backup_file"
        exit 1
    fi
    
    echo "WARNING: This will restore the database from backup!"
    echo "Database: $DB_NAME"
    echo "Backup: $backup_file"
    read -p "Continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    echo "Stopping services..."
    sudo systemctl stop sudorecon-worker sudorecon-beat sudorecon-api
    
    echo "Restoring database..."
    gunzip < "$backup_file" | sudo -u postgres psql "$DB_NAME"
    
    echo "Starting services..."
    sudo systemctl start sudorecon-api sudorecon-worker sudorecon-beat
    
    echo "Restore complete"
}

case "${1:-full}" in
    database|db)
        backup_database
        cleanup_old_backups
        ;;
    config)
        backup_config
        cleanup_old_backups
        ;;
    logs)
        backup_logs
        cleanup_old_backups
        ;;
    full)
        backup_database
        backup_config
        cleanup_old_backups
        ;;
    list)
        list_backups
        ;;
    restore)
        restore_database "$2"
        ;;
    *)
        echo "Usage: $0 {database|config|logs|full|list|restore <file>}"
        exit 1
        ;;
esac
```

### 4. Health Check Script

`/usr/local/bin/sudorecon-healthcheck`

```bash
#!/bin/bash
#
# SudoRecon Health Check
# Comprehensive health monitoring
#

set -e

NAGIOS_MODE=false
EXIT_OK=0
EXIT_WARNING=1
EXIT_CRITICAL=2
EXIT_UNKNOWN=3

function check_service() {
    local service=$1
    if systemctl is-active "$service" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

function check_api() {
    local response=$(curl -sf -w "%{http_code}" http://localhost:8080/health -o /dev/null 2>&1)
    [ "$response" = "200" ]
}

function check_database() {
    sudo -u sudorecon psql -h localhost -U sudorecon sudorecon -c "SELECT 1;" &>/dev/null
}

function check_redis() {
    redis-cli ping &>/dev/null
}

function check_disk_space() {
    local usage=$(df /var/log/sudorecon | tail -1 | awk '{print $5}' | sed 's/%//')
    [ "$usage" -lt 90 ]
}

function check_memory() {
    local available=$(free -m | awk 'NR==2 {print $7}')
    [ "$available" -gt 500 ]
}

function run_checks() {
    local exit_code=$EXIT_OK
    local messages=()
    
    # Check services
    if ! check_service sudorecon-api; then
        messages+=("API service not running")
        exit_code=$EXIT_CRITICAL
    fi
    
    if ! check_service sudorecon-worker; then
        messages+=("Worker service not running")
        exit_code=$EXIT_CRITICAL
    fi
    
    if ! check_service sudorecon-beat; then
        messages+=("Beat service not running")
        exit_code=$EXIT_WARNING
    fi
    
    # Check API endpoint
    if ! check_api; then
        messages+=("API not responding")
        exit_code=$EXIT_CRITICAL
    fi
    
    # Check database
    if ! check_database; then
        messages+=("Database connection failed")
        exit_code=$EXIT_CRITICAL
    fi
    
    # Check Redis
    if ! check_redis; then
        messages+=("Redis connection failed")
        exit_code=$EXIT_CRITICAL
    fi
    
    # Check disk space
    if ! check_disk_space; then
        messages+=("Disk space critical")
        exit_code=$EXIT_WARNING
    fi
    
    # Check memory
    if ! check_memory; then
        messages+=("Memory low")
        exit_code=$EXIT_WARNING
    fi
    
    # Output results
    if [ "$NAGIOS_MODE" = true ]; then
        if [ $exit_code -eq $EXIT_OK ]; then
            echo "OK - All checks passed"
        elif [ $exit_code -eq $EXIT_WARNING ]; then
            echo "WARNING - ${messages[@]}"
        else
            echo "CRITICAL - ${messages[@]}"
        fi
    else
        if [ $exit_code -eq $EXIT_OK ]; then
            echo "✓ All health checks passed"
        else
            echo "✗ Health check failed:"
            for msg in "${messages[@]}"; do
                echo "  - $msg"
            done
        fi
    fi
    
    exit $exit_code
}

# Parse arguments
if [ "${1:-}" = "--nagios" ]; then
    NAGIOS_MODE=true
fi

run_checks
```

---

## Monitoring Scripts

### 1. Performance Monitor

`/usr/local/bin/sudorecon-monitor`

```bash
#!/bin/bash
#
# SudoRecon Performance Monitor
# Real-time monitoring of application metrics
#

watch -n 2 '
echo "=== SudoRecon Performance Monitor ==="
echo
echo "=== Services ==="
systemctl status sudorecon-api --no-pager -l | grep Active
systemctl status sudorecon-worker --no-pager -l | grep Active
systemctl status sudorecon-beat --no-pager -l | grep Active
echo
echo "=== Resource Usage ==="
ps aux | grep "[g]unicorn\|[c]elery" | awk "{sum+=\$3; sum2+=\$4} END {printf \"CPU: %.1f%%  Memory: %.1f%%\n\", sum, sum2}"
echo
echo "=== Active Connections ==="
echo "API: $(ss -tn | grep :8080 | wc -l) connections"
echo "PostgreSQL: $(sudo -u postgres psql -t -c \"SELECT count(*) FROM pg_stat_activity WHERE datname='"'sudorecon'"';\")"
echo "Redis: $(redis-cli info clients | grep connected_clients | cut -d: -f2)"
echo
echo "=== Celery Queue ==="
sudo -u sudorecon /opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app inspect active_queues 2>/dev/null | head -20
echo
echo "=== Recent Errors (last 5 min) ==="
journalctl -u sudorecon-api -u sudorecon-worker --since "5 min ago" --no-pager | grep -i error | tail -5
'
```

### 2. SSH Connection Monitor

`/usr/local/bin/sudorecon-ssh-monitor`

```bash
#!/bin/bash
#
# Monitor SSH ControlMaster connections
#

CONTROL_PATH="/var/run/sudorecon"

echo "=== SSH ControlMaster Sockets ==="
echo
if [ -d "$CONTROL_PATH" ]; then
    echo "Active sockets:"
    ls -lh "$CONTROL_PATH"/*.sock 2>/dev/null | wc -l || echo "0"
    echo
    
    echo "Socket details:"
    find "$CONTROL_PATH" -name "*.sock" -printf "%T@ %p\n" 2>/dev/null | \
        sort -rn | head -10 | while read timestamp file; do
        echo "$(date -d @${timestamp%.*} '+%Y-%m-%d %H:%M:%S') - $(basename $file)"
    done
else
    echo "Control path not found: $CONTROL_PATH"
fi

echo
echo "=== Active SSH Processes ==="
ps aux | grep "[s]sh.*ControlMaster" | wc -l
```

---

## Cron Jobs

### Daily Maintenance Cron

`/etc/cron.d/sudorecon`

```cron
# SudoRecon Maintenance Cron Jobs
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Database maintenance (daily at 2 AM)
0 2 * * * root /usr/local/bin/sudorecon-db-maint vacuum >> /var/log/sudorecon/cron.log 2>&1

# Database statistics (daily at 6 AM)
0 6 * * * root /usr/local/bin/sudorecon-db-maint stats >> /var/log/sudorecon/cron.log 2>&1

# Backup database (daily at 1 AM)
0 1 * * * root /usr/local/bin/sudorecon-backup database >> /var/log/sudorecon/backup.log 2>&1

# Backup configuration (weekly on Sunday at 3 AM)
0 3 * * 0 root /usr/local/bin/sudorecon-backup config >> /var/log/sudorecon/backup.log 2>&1

# Health check (every 5 minutes)
*/5 * * * * root /usr/local/bin/sudorecon-healthcheck --nagios >> /var/log/sudorecon/health.log 2>&1

# Clean old logs (daily at 4 AM)
0 4 * * * root find /var/log/sudorecon -name "*.log.*" -mtime +30 -delete

# Clean old SSH sockets (hourly)
0 * * * * sudorecon find /var/run/sudorecon -name "ssh-*" -mtime +1 -delete 2>/dev/null

# Monitor disk space (every hour)
0 * * * * root df -h /var/log/sudorecon | tail -1 | awk '{if(int($5) > 80) print "WARNING: Disk usage at "$5}' | logger -t sudorecon

# Cleanup old scan jobs (weekly on Monday at 2 AM)
0 2 * * 1 root /usr/local/bin/sudorecon-db-maint cleanup 90 >> /var/log/sudorecon/cleanup.log 2>&1
```

---

## Health Checks

### Systemd Watchdog

Add to service files:

```ini
[Service]
WatchdogSec=30
Restart=on-watchdog
```

### External Monitoring Integration

#### Nagios/Icinga Plugin

`/usr/lib64/nagios/plugins/check_sudorecon`

```bash
#!/bin/bash
/usr/local/bin/sudorecon-healthcheck --nagios
```

#### Prometheus Exporter Script

`/usr/local/bin/sudorecon-metrics`

```bash
#!/bin/bash
#
# Export Prometheus-compatible metrics
#

cat << EOF
# HELP sudorecon_api_up API service status (1=up, 0=down)
# TYPE sudorecon_api_up gauge
sudorecon_api_up $(systemctl is-active sudorecon-api &>/dev/null && echo 1 || echo 0)

# HELP sudorecon_worker_up Worker service status (1=up, 0=down)
# TYPE sudorecon_worker_up gauge
sudorecon_worker_up $(systemctl is-active sudorecon-worker &>/dev/null && echo 1 || echo 0)

# HELP sudorecon_db_connections Active database connections
# TYPE sudorecon_db_connections gauge
sudorecon_db_connections $(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='sudorecon';" 2>/dev/null || echo 0)

# HELP sudorecon_disk_usage_percent Disk usage percentage
# TYPE sudorecon_disk_usage_percent gauge
sudorecon_disk_usage_percent $(df /var/log/sudorecon | tail -1 | awk '{print $5}' | sed 's/%//')
EOF
```

---

## Troubleshooting Tools

### 1. Debug Mode Script

`/usr/local/bin/sudorecon-debug`

```bash
#!/bin/bash
#
# Collect troubleshooting information
#

OUTPUT_DIR="/tmp/sudorecon-debug-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Collecting debug information..."

# System info
uname -a > "$OUTPUT_DIR/system.txt"
cat /etc/redhat-release >> "$OUTPUT_DIR/system.txt"

# Service status
systemctl status sudorecon-api > "$OUTPUT_DIR/service-api.txt" 2>&1
systemctl status sudorecon-worker > "$OUTPUT_DIR/service-worker.txt" 2>&1
systemctl status sudorecon-beat > "$OUTPUT_DIR/service-beat.txt" 2>&1

# Logs
journalctl -u sudorecon-api --since "1 hour ago" > "$OUTPUT_DIR/logs-api.txt" 2>&1
journalctl -u sudorecon-worker --since "1 hour ago" > "$OUTPUT_DIR/logs-worker.txt" 2>&1
tail -1000 /var/log/sudorecon/*.log > "$OUTPUT_DIR/application-logs.txt" 2>&1

# Process info
ps aux | grep "[g]unicorn\|[c]elery" > "$OUTPUT_DIR/processes.txt"

# Network info
ss -tulpn | grep -E "8080|5432|6379" > "$OUTPUT_DIR/network.txt"

# Database info
sudo -u postgres psql sudorecon -c "\l+" > "$OUTPUT_DIR/db-databases.txt" 2>&1
sudo -u postgres psql sudorecon -c "\dt+" > "$OUTPUT_DIR/db-tables.txt" 2>&1
sudo -u postgres psql sudorecon -c "SELECT * FROM pg_stat_activity;" > "$OUTPUT_DIR/db-activity.txt" 2>&1

# Configuration (sanitized)
cat /etc/sudorecon/.env | grep -v "PASSWORD\|SECRET\|KEY" > "$OUTPUT_DIR/config-sanitized.txt" 2>&1

# Package tar
tar czf "$OUTPUT_DIR.tar.gz" -C /tmp "$(basename "$OUTPUT_DIR")"
rm -rf "$OUTPUT_DIR"

echo "Debug information collected: $OUTPUT_DIR.tar.gz"
echo "Please send this file to support"
```

### 2. Connection Test Script

`/usr/local/bin/sudorecon-test-conn`

```bash
#!/bin/bash
#
# Test connectivity to all dependencies
#

function test_connection() {
    local name=$1
    local host=$2
    local port=$3
    
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        echo "✓ $name ($host:$port): Connected"
        return 0
    else
        echo "✗ $name ($host:$port): Connection failed"
        return 1
    fi
}

echo "Testing SudoRecon connectivity..."
echo

test_connection "PostgreSQL" "localhost" "5432"
test_connection "Redis" "localhost" "6379"
test_connection "API" "localhost" "8080"

echo
echo "Testing API health endpoint..."
curl -sf http://localhost:8080/health && echo "✓ API health check passed" || echo "✗ API health check failed"

echo
echo "Testing database query..."
sudo -u sudorecon psql -h localhost -U sudorecon sudorecon -c "SELECT count(*) FROM servers;" && \
    echo "✓ Database query successful" || echo "✗ Database query failed"
```

---

## Performance Monitoring

### Application Metrics Script

`/usr/local/bin/sudorecon-stats`

```bash
#!/bin/bash
#
# Display application statistics
#

sudo -u sudorecon /opt/sudorecon/app/venv/bin/python << 'EOF'
from backend.db.session import SessionLocal
from backend.models import Server, SudoLog, ScanJob, SudoProvision
from sqlalchemy import func
from datetime import datetime, timedelta

db = SessionLocal()

try:
    print("=== SudoRecon Statistics ===\n")
    
    # Server counts
    total_servers = db.query(func.count(Server.id)).scalar()
    print(f"Total Servers: {total_servers}")
    
    # Log counts
    total_logs = db.query(func.count(SudoLog.id)).scalar()
    logs_24h = db.query(func.count(SudoLog.id)).filter(
        SudoLog.created_at > datetime.utcnow() - timedelta(hours=24)
    ).scalar()
    print(f"Total Logs: {total_logs:,}")
    print(f"Logs (24h): {logs_24h:,}")
    
    # Scan job stats
    jobs_pending = db.query(func.count(ScanJob.id)).filter(
        ScanJob.status == 'pending'
    ).scalar()
    jobs_running = db.query(func.count(ScanJob.id)).filter(
        ScanJob.status == 'running'
    ).scalar()
    print(f"Scan Jobs Pending: {jobs_pending}")
    print(f"Scan Jobs Running: {jobs_running}")
    
    # Provision stats
    active_provisions = db.query(func.count(SudoProvision.id)).filter(
        SudoProvision.status == 'active'
    ).scalar()
    print(f"Active Provisions: {active_provisions}")
    
    print("\n=== Top 5 Active Servers (by log count) ===")
    top_servers = db.query(
        Server.hostname,
        func.count(SudoLog.id).label('log_count')
    ).join(SudoLog).group_by(Server.id).order_by(
        func.count(SudoLog.id).desc()
    ).limit(5).all()
    
    for server, count in top_servers:
        print(f"  {server}: {count:,} logs")
    
finally:
    db.close()
EOF
```

---

## Installation

### Install All Tools

```bash
# Create scripts directory
sudo mkdir -p /usr/local/bin

# Copy all scripts
sudo cp scripts/sudorecon-* /usr/local/bin/

# Make executable
sudo chmod +x /usr/local/bin/sudorecon-*

# Install cron jobs
sudo cp cron.d/sudorecon /etc/cron.d/

# Install logrotate config
sudo cp logrotate.d/sudorecon /etc/logrotate.d/

# Test installation
sudorecon-service status
sudorecon-healthcheck
```

---

## Summary

This comprehensive systemd integration provides:

1. **Hardened systemd service units** with security features
2. **Service management tools** for easy operations
3. **Automated maintenance** via cron jobs
4. **Health monitoring** and alerting
5. **Backup and restore** capabilities
6. **Performance monitoring** scripts
7. **Troubleshooting tools** for rapid diagnosis
8. **Database maintenance** automation
9. **Log management** with rotation
10. **Integration points** for external monitoring (Nagios, Prometheus)

All tools are production-ready and follow RHEL9 best practices.
