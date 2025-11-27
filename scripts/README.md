# SudoRecon Administrative Scripts

This directory contains administrative and monitoring scripts for SudoRecon on RHEL9.

## Installation

```bash
# Copy scripts to system location
sudo cp scripts/* /usr/local/bin/
sudo chmod +x /usr/local/bin/sudorecon-*

# Copy systemd units
sudo cp systemd/*.target /etc/systemd/system/
sudo systemctl daemon-reload

# Copy configuration files
sudo cp config/logrotate-sudorecon /etc/logrotate.d/sudorecon
sudo cp config/cron-sudorecon /etc/cron.d/sudorecon
```

## Available Scripts

### Service Management

**`sudorecon-service`** - Main service control
```bash
sudorecon-service start       # Start all services
sudorecon-service stop        # Stop all services
sudorecon-service restart     # Restart all services
sudorecon-service status      # Show service status
sudorecon-service health      # Comprehensive health check
sudorecon-service logs [service] [lines]  # View logs
```

### Backup & Restore

**`sudorecon-backup`** - Backup management
```bash
sudorecon-backup database     # Backup database only
sudorecon-backup config       # Backup configuration
sudorecon-backup logs         # Backup recent logs
sudorecon-backup full         # Full backup (default)
sudorecon-backup list         # List available backups
sudorecon-backup restore <file>  # Restore from backup
```

Backups are stored in `/var/backups/sudorecon/` with 30-day retention.

### Health Monitoring

**`sudorecon-healthcheck`** - System health check
```bash
sudorecon-healthcheck              # Interactive health check
sudorecon-healthcheck --nagios     # Nagios-compatible output
```

Checks:
- Service status (API, Worker, Beat)
- Database connectivity
- Redis connectivity
- API endpoint health
- Disk space usage
- Memory availability

### Database Maintenance

**`sudorecon-db-maint`** - Database operations
```bash
sudorecon-db-maint vacuum          # Run VACUUM ANALYZE
sudorecon-db-maint stats           # Show database statistics
sudorecon-db-maint cleanup [days]  # Clean old data (default: 90 days)
sudorecon-db-maint all             # Run all maintenance tasks
```

### Statistics

**`sudorecon-stats`** - Application statistics
```bash
sudorecon-stats
```

Displays:
- Total servers monitored
- Log counts (total and 24h)
- Scan job status
- Active provisions
- Top 5 most active servers

## Automated Tasks (Cron)

The cron configuration (`/etc/cron.d/sudorecon`) runs:

| Task | Schedule | Description |
|------|----------|-------------|
| Database VACUUM | Daily 2 AM | Optimize database |
| Database stats | Daily 6 AM | Collect statistics |
| Database backup | Daily 1 AM | Full DB backup |
| Config backup | Sunday 3 AM | Weekly config backup |
| Health check | Every 5 min | Monitor system health |
| Log cleanup | Daily 4 AM | Remove logs >30 days |
| SSH socket cleanup | Hourly | Clean stale sockets |
| Disk space monitor | Hourly | Alert if >80% usage |
| Data cleanup | Monday 2 AM | Remove old scan jobs |

## Log Rotation

Logrotate configuration (`/etc/logrotate.d/sudorecon`):

- **Application logs**: 30-day rotation, daily
- **API access logs**: 90-day rotation, daily or when >100MB
- Compressed with delayed compression
- Automatic service reload after rotation

## Example Usage

### Daily Operations

```bash
# Morning health check
sudorecon-service health

# View recent API logs
sudorecon-service logs sudorecon-api 100

# Check application statistics
sudorecon-stats

# View database size and performance
sudorecon-db-maint stats
```

### Weekly Maintenance

```bash
# Full database maintenance
sudorecon-db-maint all

# Review backups
sudorecon-backup list

# Check for old data to clean
sudorecon-db-maint cleanup 90
```

### Troubleshooting

```bash
# Check service status
sudorecon-service status

# View recent errors
journalctl -u sudorecon-api --since "1 hour ago" | grep -i error

# Full health check
sudorecon-healthcheck

# Test database connection
sudo -u sudorecon psql -h localhost -U sudorecon sudorecon -c "SELECT version();"

# Check Redis
redis-cli ping

# View worker queue status
sudo -u sudorecon /opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app inspect active
```

### Emergency Recovery

```bash
# Stop all services
sudorecon-service stop

# Restore from backup
sudorecon-backup restore /var/backups/sudorecon/sudorecon_db_20240101_120000.sql.gz

# Start services
sudorecon-service start

# Verify health
sudorecon-service health
```

## Monitoring Integration

### Nagios/Icinga

```bash
# Add to Nagios plugins
sudo ln -s /usr/local/bin/sudorecon-healthcheck /usr/lib64/nagios/plugins/check_sudorecon

# Nagios command definition
define command {
    command_name    check_sudorecon
    command_line    $USER1$/check_sudorecon --nagios
}

# Service definition
define service {
    use                     generic-service
    host_name               sudorecon-server
    service_description     SudoRecon Health
    check_command           check_sudorecon
    check_interval          5
    retry_interval          1
}
```

### Prometheus Metrics

Health check metrics can be exposed for Prometheus scraping. Add to `/etc/systemd/system/sudorecon-metrics.timer`:

```ini
[Unit]
Description=SudoRecon Metrics Export Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
```

## File Permissions

Scripts should be executable by root:

```bash
sudo chown root:root /usr/local/bin/sudorecon-*
sudo chmod 755 /usr/local/bin/sudorecon-*
```

## Logging

All automated tasks log to:
- `/var/log/sudorecon/cron.log` - Cron job output
- `/var/log/sudorecon/backup.log` - Backup operations
- `/var/log/sudorecon/health.log` - Health check results
- `/var/log/sudorecon/db-maintenance.log` - Database maintenance
- `/var/log/sudorecon/cleanup.log` - Data cleanup operations

## Support

For detailed documentation, see:
- `SYSTEMD_INTEGRATION.md` - Complete systemd guide
- `DEPLOYMENT_RHEL9.md` - Deployment instructions
- `README.md` - General application documentation
