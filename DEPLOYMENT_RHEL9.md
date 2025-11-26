# SudoRecon Deployment Guide for RHEL 9

This guide provides comprehensive deployment instructions for SudoRecon on Red Hat Enterprise Linux 9 (RHEL 9) using two different approaches:

1. **Python Virtual Environment (venv)** - Traditional deployment with systemd services
2. **Podman Containers** - Containerized deployment using rootless Podman

## Table of Contents

- [Prerequisites](#prerequisites)
- [Method 1: Python venv Deployment](#method-1-python-venv-deployment)
- [Method 2: Podman Deployment](#method-2-podman-deployment)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- RHEL 9.x (or compatible: Rocky Linux 9, AlmaLinux 9)
- Minimum 4GB RAM (8GB recommended)
- Minimum 20GB disk space
- Root or sudo access
- Network connectivity for package installation

### Common Prerequisites (Both Methods)

```bash
# Update system packages
sudo dnf update -y

# Install EPEL repository (if not already installed)
sudo dnf install -y epel-release

# Install common utilities
sudo dnf install -y git wget curl vim

# Enable and configure firewall (if not already done)
sudo systemctl enable --now firewalld
```

---

## Method 1: Python venv Deployment

This method deploys SudoRecon using Python virtual environments and systemd service units.

### 1.1 Install System Dependencies

```bash
# Install Python 3.11 and development tools
sudo dnf install -y python3.11 python3.11-pip python3.11-devel

# Install PostgreSQL 15
sudo dnf install -y postgresql15-server postgresql15-contrib postgresql15-devel

# Install Redis
sudo dnf install -y redis

# Install Node.js 20 (for frontend)
sudo dnf module reset nodejs -y
sudo dnf module enable nodejs:20 -y
sudo dnf install -y nodejs npm

# Install system dependencies for Python packages
sudo dnf install -y gcc make openssl-devel bzip2-devel libffi-devel

# Install SSH client (usually pre-installed)
sudo dnf install -y openssh-clients
```

### 1.2 Create Service User

```bash
# Create sudorecon system user
sudo useradd -r -m -d /opt/sudorecon -s /bin/bash sudorecon

# Set up SSH directory for the service user
sudo mkdir -p /opt/sudorecon/.ssh
sudo chmod 700 /opt/sudorecon/.ssh
sudo chown -R sudorecon:sudorecon /opt/sudorecon/.ssh
```

### 1.3 Configure PostgreSQL

```bash
# Initialize PostgreSQL database
sudo /usr/pgsql-15/bin/postgresql-15-setup initdb

# Start and enable PostgreSQL
sudo systemctl enable --now postgresql-15

# Create database and user
sudo -u postgres psql << EOF
CREATE USER sudorecon WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE sudorecon OWNER sudorecon;
GRANT ALL PRIVILEGES ON DATABASE sudorecon TO sudorecon;
\q
EOF

# Configure PostgreSQL to accept local connections (if needed)
# Edit /var/lib/pgsql/15/data/pg_hba.conf
sudo bash -c 'cat >> /var/lib/pgsql/15/data/pg_hba.conf << EOF
# SudoRecon application
local   sudorecon       sudorecon                               scram-sha-256
host    sudorecon       sudorecon       127.0.0.1/32            scram-sha-256
host    sudorecon       sudorecon       ::1/128                 scram-sha-256
EOF'

# Reload PostgreSQL configuration
sudo systemctl reload postgresql-15
```

### 1.4 Configure Redis

```bash
# Configure Redis
sudo sed -i 's/^bind 127.0.0.1/bind 127.0.0.1/g' /etc/redis/redis.conf
sudo sed -i 's/^# requirepass foobared/requirepass your_redis_password/g' /etc/redis/redis.conf

# Start and enable Redis
sudo systemctl enable --now redis
```

### 1.5 Install SudoRecon Application

```bash
# Switch to sudorecon user
sudo su - sudorecon

# Clone the repository
cd /opt/sudorecon
git clone https://github.com/yourusername/SudoRecon.git app
cd app

# Create Python virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install application
pip install -e .

# Install production dependencies
pip install gunicorn

# Exit sudorecon user
exit
```

### 1.6 Configure Application

```bash
# Create configuration file
sudo mkdir -p /etc/sudorecon
sudo cp /opt/sudorecon/app/.env.example /etc/sudorecon/.env

# Edit configuration (use your actual passwords and settings)
sudo vim /etc/sudorecon/.env
```

**Example `/etc/sudorecon/.env`:**

```bash
# Application
APP_NAME=SudoRecon
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://sudorecon:your_secure_password_here@localhost:5432/sudorecon

# Redis
REDIS_URL=redis://:your_redis_password@localhost:6379/0
CELERY_BROKER_URL=redis://:your_redis_password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:your_redis_password@localhost:6379/2

# API
API_HOST=0.0.0.0
API_PORT=8080
CORS_ORIGINS=["http://localhost:3000","http://yourdomain.com"]

# Security
JWT_SECRET=generate_random_secret_here_minimum_32_chars
API_KEY_HASH_ALGORITHM=sha256

# SSH Configuration
SSH_USER=sudorecon
SSH_KEY_PATH=/opt/sudorecon/.ssh/id_rsa
SSH_CONTROL_PATH=/var/run/sudorecon/ssh-%r@%h:%p
SSH_CONNECT_TIMEOUT=10
SSH_MAX_CONNECTIONS=200

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

```bash
# Set proper permissions
sudo chown root:sudorecon /etc/sudorecon/.env
sudo chmod 640 /etc/sudorecon/.env

# Create runtime directory
sudo mkdir -p /var/run/sudorecon
sudo chown sudorecon:sudorecon /var/run/sudorecon
sudo chmod 755 /var/run/sudorecon

# Create log directory
sudo mkdir -p /var/log/sudorecon
sudo chown sudorecon:sudorecon /var/log/sudorecon
sudo chmod 755 /var/log/sudorecon
```

### 1.7 Run Database Migrations

```bash
# Run as sudorecon user
sudo su - sudorecon
cd /opt/sudorecon/app
source venv/bin/activate

# Run migrations
alembic upgrade head

exit
```

### 1.8 Create Systemd Service Units

**API Service:** `/etc/systemd/system/sudorecon-api.service`

```bash
sudo tee /etc/systemd/system/sudorecon-api.service > /dev/null << 'EOF'
[Unit]
Description=SudoRecon API Service
After=network.target postgresql-15.service redis.service
Requires=postgresql-15.service redis.service

[Service]
Type=notify
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env
ExecStart=/opt/sudorecon/app/venv/bin/gunicorn \
    backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8080 \
    --timeout 120 \
    --access-logfile /var/log/sudorecon/api-access.log \
    --error-logfile /var/log/sudorecon/api-error.log \
    --log-level info
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Celery Worker Service:** `/etc/systemd/system/sudorecon-worker.service`

```bash
sudo tee /etc/systemd/system/sudorecon-worker.service > /dev/null << 'EOF'
[Unit]
Description=SudoRecon Celery Worker
After=network.target redis.service postgresql-15.service
Requires=redis.service postgresql-15.service

[Service]
Type=forking
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env
ExecStart=/opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app worker \
    --loglevel=info \
    --logfile=/var/log/sudorecon/worker.log \
    --pidfile=/var/run/sudorecon/worker.pid
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Celery Beat Service:** `/etc/systemd/system/sudorecon-beat.service`

```bash
sudo tee /etc/systemd/system/sudorecon-beat.service > /dev/null << 'EOF'
[Unit]
Description=SudoRecon Celery Beat Scheduler
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app
EnvironmentFile=/etc/sudorecon/.env
ExecStart=/opt/sudorecon/app/venv/bin/celery -A backend.tasks.celery_app beat \
    --loglevel=info \
    --logfile=/var/log/sudorecon/beat.log \
    --pidfile=/var/run/sudorecon/beat.pid
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

**Frontend Service (Optional - Production should use nginx):** `/etc/systemd/system/sudorecon-frontend.service`

```bash
sudo tee /etc/systemd/system/sudorecon-frontend.service > /dev/null << 'EOF'
[Unit]
Description=SudoRecon Frontend Development Server
After=network.target

[Service]
Type=simple
User=sudorecon
Group=sudorecon
WorkingDirectory=/opt/sudorecon/app/frontend
Environment=VITE_API_URL=http://localhost:8080
ExecStartPre=/usr/bin/npm install
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### 1.9 Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable sudorecon-api sudorecon-worker sudorecon-beat
sudo systemctl start sudorecon-api sudorecon-worker sudorecon-beat

# Check status
sudo systemctl status sudorecon-api
sudo systemctl status sudorecon-worker
sudo systemctl status sudorecon-beat
```

### 1.10 Configure Firewall

```bash
# Allow API port
sudo firewall-cmd --permanent --add-port=8080/tcp

# Allow frontend port (if running development server)
sudo firewall-cmd --permanent --add-port=3000/tcp

# Reload firewall
sudo firewall-cmd --reload
```

### 1.11 Build and Deploy Frontend (Production)

For production, build the frontend and serve it with nginx:

```bash
# Build frontend
sudo su - sudorecon
cd /opt/sudorecon/app/frontend
npm install
npm run build
exit

# Install nginx
sudo dnf install -y nginx

# Create nginx configuration
sudo tee /etc/nginx/conf.d/sudorecon.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /opt/sudorecon/app/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable and start nginx
sudo systemctl enable --now nginx

# Configure firewall for HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Method 2: Podman Deployment

This method uses rootless Podman containers for a more isolated deployment.

### 2.1 Install Podman and Dependencies

```bash
# Install Podman
sudo dnf install -y podman podman-compose

# Install podman-docker for docker-compose compatibility (optional)
sudo dnf install -y podman-docker

# Enable podman socket for rootless mode
systemctl --user enable --now podman.socket
```

### 2.2 Create Service User

```bash
# Create sudorecon user
sudo useradd -m -s /bin/bash sudorecon

# Allow lingering for the user (enables user services to run at boot)
sudo loginctl enable-linger sudorecon
```

### 2.3 Set Up Application

```bash
# Switch to sudorecon user
sudo su - sudorecon

# Clone repository
cd ~
git clone https://github.com/yourusername/SudoRecon.git
cd SudoRecon

# Create environment file
cp .env.example .env

# Edit configuration
vim .env
```

**Example `.env` for Podman:**

```bash
# Application
APP_NAME=SudoRecon
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://sudorecon:secure_password@db:5432/sudorecon

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# API
API_HOST=0.0.0.0
API_PORT=8080

# Security
JWT_SECRET=generate_random_secret_here_minimum_32_chars

# SSH
SSH_USER=sudorecon
SSH_KEY_PATH=/home/sudorecon/.ssh/id_rsa
SSH_CONTROL_PATH=/var/run/sudorecon/ssh-%r@%h:%p
```

### 2.4 Create Podman Compose File

Create `docker-compose.podman.yml`:

```yaml
version: '3.8'

services:
  db:
    image: docker.io/library/postgres:15-alpine
    container_name: sudorecon-db
    environment:
      POSTGRES_USER: sudorecon
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: sudorecon
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sudorecon"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: docker.io/library/redis:7-alpine
    container_name: sudorecon-redis
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: sudorecon-api
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./backend:/app/backend:z
      - ssh-sockets:/var/run/sudorecon:z
      - ${HOME}/.ssh:/home/sudorecon/.ssh:ro,z
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080

  worker:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: sudorecon-worker
    env_file:
      - .env
    volumes:
      - ./backend:/app/backend:z
      - ssh-sockets:/var/run/sudorecon:z
      - ${HOME}/.ssh:/home/sudorecon/.ssh:ro,z
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: celery -A backend.tasks.celery_app worker --loglevel=info

  beat:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: sudorecon-beat
    env_file:
      - .env
    depends_on:
      - redis
    command: celery -A backend.tasks.celery_app beat --loglevel=info

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: sudorecon-frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app:z
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8080
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres-data:
  redis-data:
  ssh-sockets:
```

### 2.5 Build and Start Containers

```bash
# Still as sudorecon user
cd ~/SudoRecon

# Build images
podman-compose -f docker-compose.podman.yml build

# Start services
podman-compose -f docker-compose.podman.yml up -d

# Check status
podman ps

# View logs
podman logs sudorecon-api
podman logs sudorecon-worker
```

### 2.6 Run Database Migrations

```bash
# Run migrations inside API container
podman exec sudorecon-api alembic upgrade head
```

### 2.7 Create Systemd User Services

Create systemd user service to start containers at boot:

```bash
# Create systemd user directory
mkdir -p ~/.config/systemd/user

# Generate systemd unit files
cd ~/SudoRecon
podman generate systemd --new --files --name sudorecon-db
podman generate systemd --new --files --name sudorecon-redis
podman generate systemd --new --files --name sudorecon-api
podman generate systemd --new --files --name sudorecon-worker
podman generate systemd --new --files --name sudorecon-beat
podman generate systemd --new --files --name sudorecon-frontend

# Move unit files to systemd directory
mv container-*.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable services
systemctl --user enable container-sudorecon-db.service
systemctl --user enable container-sudorecon-redis.service
systemctl --user enable container-sudorecon-api.service
systemctl --user enable container-sudorecon-worker.service
systemctl --user enable container-sudorecon-beat.service
systemctl --user enable container-sudorecon-frontend.service

# Exit sudorecon user
exit
```

### 2.8 Configure Firewall

```bash
# Allow API and frontend ports
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

### 2.9 Optional: Set Up Reverse Proxy

For production, use nginx as a reverse proxy:

```bash
# Install nginx
sudo dnf install -y nginx

# Create nginx configuration
sudo tee /etc/nginx/conf.d/sudorecon.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable and start nginx
sudo systemctl enable --now nginx

# Configure SELinux (if enforcing)
sudo setsebool -P httpd_can_network_connect 1

# Configure firewall
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## Post-Deployment Configuration

### Set Up SSH Keys

For both deployment methods, configure SSH keys for the sudorecon user:

```bash
# Switch to sudorecon user
sudo su - sudorecon

# Generate SSH key pair (if not already exists)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# Display public key to copy to target servers
cat ~/.ssh/id_rsa.pub

# Exit sudorecon user
exit
```

Copy the public key to all target servers' `authorized_keys` for the monitoring user.

### Configure SSL/TLS (Production)

For production deployments, use Let's Encrypt:

```bash
# Install certbot
sudo dnf install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Set up automatic renewal
sudo systemctl enable --now certbot-renew.timer
```

### Create Initial Admin User

```bash
# Using venv method
sudo su - sudorecon
cd /opt/sudorecon/app
source venv/bin/activate
python -c "from backend.utils.create_admin import create_admin; create_admin('admin', 'admin@example.com', 'secure_password')"
exit

# Using Podman method
podman exec -it sudorecon-api python -c "from backend.utils.create_admin import create_admin; create_admin('admin', 'admin@example.com', 'secure_password')"
```

---

## Monitoring and Maintenance

### Check Service Status

**venv method:**
```bash
sudo systemctl status sudorecon-api
sudo systemctl status sudorecon-worker
sudo systemctl status sudorecon-beat
```

**Podman method:**
```bash
sudo su - sudorecon
podman ps
systemctl --user status container-sudorecon-api.service
exit
```

### View Logs

**venv method:**
```bash
# View service logs
sudo journalctl -u sudorecon-api -f
sudo journalctl -u sudorecon-worker -f

# View application logs
sudo tail -f /var/log/sudorecon/api-access.log
sudo tail -f /var/log/sudorecon/api-error.log
```

**Podman method:**
```bash
podman logs -f sudorecon-api
podman logs -f sudorecon-worker
```

### Backup Database

```bash
# venv method
sudo -u postgres pg_dump sudorecon > sudorecon_backup_$(date +%Y%m%d).sql

# Podman method
podman exec sudorecon-db pg_dump -U sudorecon sudorecon > sudorecon_backup_$(date +%Y%m%d).sql
```

### Update Application

**venv method:**
```bash
sudo systemctl stop sudorecon-api sudorecon-worker sudorecon-beat

sudo su - sudorecon
cd /opt/sudorecon/app
git pull
source venv/bin/activate
pip install -e .
alembic upgrade head
exit

sudo systemctl start sudorecon-api sudorecon-worker sudorecon-beat
```

**Podman method:**
```bash
sudo su - sudorecon
cd ~/SudoRecon
podman-compose -f docker-compose.podman.yml down
git pull
podman-compose -f docker-compose.podman.yml build
podman-compose -f docker-compose.podman.yml up -d
podman exec sudorecon-api alembic upgrade head
exit
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

Check what's using the port:
```bash
sudo ss -tulpn | grep :8080
```

#### SELinux Denials

Check audit log:
```bash
sudo ausearch -m avc -ts recent
```

Temporarily set SELinux to permissive for testing:
```bash
sudo setenforce 0
```

#### Podman Permission Issues

Ensure the user has proper subuid/subgid mappings:
```bash
cat /etc/subuid
cat /etc/subgid
```

#### Database Connection Issues

Test PostgreSQL connection:
```bash
psql -h localhost -U sudorecon -d sudorecon
```

#### Redis Connection Issues

Test Redis connection:
```bash
redis-cli -h localhost ping
```

### Service Won't Start

Check logs for errors:
```bash
# venv
sudo journalctl -xeu sudorecon-api

# Podman
podman logs sudorecon-api
```

### Enable Debug Logging

Edit `/etc/sudorecon/.env` (venv) or `.env` (Podman):
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart services.

---

## Performance Tuning

### PostgreSQL Tuning

Edit `/var/lib/pgsql/15/data/postgresql.conf`:

```ini
# Memory settings (adjust based on available RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
work_mem = 8MB

# Connection settings
max_connections = 200

# WAL settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### Gunicorn Workers

Adjust workers in systemd service file:
```bash
# Formula: (2 x CPU cores) + 1
--workers 9  # for 4-core system
```

### Celery Workers

Increase concurrency:
```bash
celery -A backend.tasks.celery_app worker --concurrency=8
```

---

## Security Hardening

### 1. Firewall Configuration

Only allow necessary ports:
```bash
sudo firewall-cmd --permanent --remove-service=cockpit
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" port port="8080" protocol="tcp" accept'
sudo firewall-cmd --reload
```

### 2. SELinux Configuration

Keep SELinux enforcing and create custom policy if needed.

### 3. Limit SSH Access

Configure `/opt/sudorecon/.ssh/config`:
```
Host *
    StrictHostKeyChecking accept-new
    UserKnownHostsFile /opt/sudorecon/.ssh/known_hosts
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ConnectTimeout 10
```

### 4. Regular Updates

```bash
# Set up automatic security updates
sudo dnf install -y dnf-automatic
sudo systemctl enable --now dnf-automatic.timer
```

---

## Additional Resources

- [SudoRecon Documentation](https://github.com/yourusername/SudoRecon)
- [RHEL 9 Documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9)
- [Podman Documentation](https://docs.podman.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/SudoRecon/issues
- Email: support@yourdomain.com

---

**Last Updated:** November 2025
**Version:** 1.0.0
