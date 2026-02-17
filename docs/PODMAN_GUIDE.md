# Podman Deployment Guide

## Why Podman?

Podman is a daemonless container engine that's compatible with Docker but offers several advantages:
- ✅ **No Docker Desktop Required** - Free for all use cases
- ✅ **Rootless Containers** - Better security
- ✅ **Daemonless** - No background daemon consuming resources
- ✅ **Docker Compatible** - Uses same Dockerfile and docker-compose.yml formats
- ✅ **Lightweight** - Lower resource usage than Docker Desktop

## Quick Start

### 1. Install Podman

Run the installation script:
```batch
PODMAN_INSTALL.bat
```

This will:
1. Open the Podman download page
2. Install podman-compose via pip
3. Initialize and start the Podman machine
4. Verify installation

**Manual Installation:**
1. Download Podman for Windows: https://github.com/containers/podman/releases
2. Run the installer with default settings
3. Install Python 3.8+ if not already installed
4. Install podman-compose: `pip install podman-compose`
5. Initialize: `podman machine init`
6. Start: `podman machine start`

### 2. Start All Services

```batch
PODMAN_START.bat
```

This starts:
- **Portainer** (Container Management UI)
- **PostgreSQL** (Database)
- **Redis** (Cache & Message Broker)
- **Backend API** (FastAPI Application)
- **Celery Workers** (Background Task Processing)
- **Celery Beat** (Scheduled Tasks)

**All containers restart automatically on system boot!**

### 3. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| **Portainer** | http://localhost:9000 | Container management UI |
| **Backend API** | http://localhost:8002 | FastAPI application |
| **API Docs** | http://localhost:8002/docs | Swagger UI documentation |
| **PostgreSQL** | localhost:5433 | Database connection |
| **Redis** | localhost:6379 | Cache & broker |

### 4. Stop Services

```batch
PODMAN_STOP.bat
```

## Available Commands

### PODMAN_INSTALL.bat
One-time installation and setup of Podman and dependencies.

### PODMAN_START.bat
Start all services in detached mode (background).
- Automatically starts Podman machine if not running
- Containers restart automatically on system boot
- Opens Portainer and API docs in browser

### PODMAN_STOP.bat
Gracefully stop all running containers.

### PODMAN_RESTART.bat
Restart all services (useful after configuration changes).

### PODMAN_LOGS.bat
View real-time logs from all services.
- Press Ctrl+C to exit

### PODMAN_CLEANUP.bat
⚠️ **WARNING**: Removes all containers, volumes, and data!
- Use this to completely reset the system
- All database data will be lost

## Podman Machine Management

### Start Podman Machine
```batch
podman machine start
```

### Stop Podman Machine
```batch
podman machine stop
```

### Check Podman Machine Status
```batch
podman machine list
```

### Podman Machine Info
```batch
podman machine info
```

## Container Management with Portainer

Portainer provides a web-based UI for managing containers:

1. **First-Time Setup:**
   - Open http://localhost:9000
   - Create admin username and password
   - Select "Get Started" to connect to local environment

2. **Managing Containers:**
   - View all running containers
   - Start/stop/restart containers
   - View logs in real-time
   - Access container shells
   - Monitor resource usage

3. **Managing Volumes:**
   - View persistent data volumes
   - Backup volumes
   - Clean up unused volumes

4. **Managing Images:**
   - View downloaded images
   - Pull new images
   - Remove unused images

## Database Management

### Access PostgreSQL Database

**Using psql:**
```batch
podman exec -it yolo_postgres psql -U yolo_user -d yolo_assembly
```

**Using Portainer:**
1. Open Portainer → Containers
2. Click on `yolo_postgres`
3. Click "Console" → Select `/bin/sh`
4. Run: `psql -U yolo_user -d yolo_assembly`

### Database Backup

```batch
podman exec yolo_postgres pg_dump -U yolo_user yolo_assembly > backup.sql
```

### Database Restore

```batch
podman exec -i yolo_postgres psql -U yolo_user yolo_assembly < backup.sql
```

## Redis Management

### Access Redis CLI

```batch
podman exec -it yolo_redis redis-cli
```

### Monitor Redis

```batch
podman exec -it yolo_redis redis-cli MONITOR
```

## Viewing Logs

### All Services

```batch
PODMAN_LOGS.bat
```

### Specific Service

```batch
podman-compose logs -f backend
podman-compose logs -f celery_worker
podman-compose logs -f postgres
```

### View Last 100 Lines

```batch
podman-compose logs --tail=100 backend
```

## Development Workflow

### Making Code Changes

1. Edit code in `backend/` directory
2. Restart containers: `PODMAN_RESTART.bat`
3. Changes will be reflected immediately

### Rebuilding After Dependency Changes

If you modify `requirements.txt`:

```batch
podman-compose build --no-cache
podman-compose up -d
```

### Accessing Container Shell

```batch
podman exec -it yolo_backend /bin/bash
```

## Auto-Start on System Boot

### Current Configuration: ✅ Enabled

All containers use `restart: unless-stopped` policy:
- Containers start automatically when Podman machine starts
- Containers restart if they crash
- Containers stay stopped if you manually stop them

### Configure Podman Machine Auto-Start

**Option 1: Windows Startup (Recommended)**
Create a startup task:
1. Press Win+R, type `shell:startup`
2. Create a shortcut to: `C:\Program Files\RedHat\Podman\podman.exe machine start`

**Option 2: Windows Service**
```batch
podman machine set --now --rootful=false --cpus 2 --memory 4096
```

## Resource Management

### View Container Stats

```batch
podman stats
```

### View Disk Usage

```batch
podman system df
```

### Clean Up Unused Resources

```batch
podman system prune -af --volumes
```

## Troubleshooting

### Podman Machine Won't Start

```batch
podman machine stop
podman machine rm
podman machine init
podman machine start
```

### Containers Won't Start

Check logs:
```batch
PODMAN_LOGS.bat
```

Or specific service:
```batch
podman-compose logs backend
```

### Port Already in Use

If port 8002 or 9000 is already taken:
1. Edit `docker-compose.yml`
2. Change port mapping (e.g., `"8003:8002"`)
3. Restart: `PODMAN_RESTART.bat`

### Database Connection Errors

Check if PostgreSQL is healthy:
```batch
podman-compose ps
```

You should see:
```
yolo_postgres   Up (healthy)
```

If unhealthy, check logs:
```batch
podman-compose logs postgres
```

### Reset Everything

```batch
PODMAN_CLEANUP.bat
PODMAN_START.bat
```

## Migrating from Docker

If you have Docker installed, Podman can run alongside it without conflicts:

1. Podman uses different socket/daemon
2. Can use same Dockerfile and docker-compose.yml
3. Commands are identical (just replace `docker` with `podman`)

### Alias Podman as Docker

If you want to use `docker` commands:

**PowerShell:**
```powershell
Set-Alias -Name docker -Value podman
Set-Alias -Name docker-compose -Value podman-compose
```

**Command Prompt:**
```batch
doskey docker=podman $*
doskey docker-compose=podman-compose $*
```

## Production Deployment

For production, update these settings in `docker-compose.yml`:

```yaml
environment:
  DEBUG: "False"
  SECRET_KEY: "GENERATE_SECURE_RANDOM_KEY_HERE"
  DATABASE_URL: "postgresql://secure_user:secure_pass@postgres:5432/yolo_assembly"
  CORS_ORIGINS: '["https://your-production-domain.com"]'
```

Security recommendations:
- [ ] Change `SECRET_KEY`
- [ ] Use strong database password
- [ ] Set `DEBUG: "False"`
- [ ] Configure proper CORS origins
- [ ] Use HTTPS in production
- [ ] Don't expose database ports publicly
- [ ] Regular security updates
- [ ] Enable rootless mode

## Advanced Configuration

### Increase Podman Machine Resources

```batch
podman machine set --cpus 4
podman machine set --memory 8192
podman machine set --disk-size 100
```

Then restart:
```batch
podman machine stop
podman machine start
```

### Enable SSH to Podman Machine

```batch
podman machine ssh
```

### Custom Networks

View networks:
```batch
podman network ls
```

Inspect network:
```batch
podman network inspect yolo_network
```

## Performance Tips

1. **Increase Machine Resources:**
   - Allocate more CPU/RAM for better performance
   - Default: 2 CPUs, 2GB RAM

2. **Use Named Volumes:**
   - Already configured in docker-compose.yml
   - Better performance than bind mounts

3. **Optimize Images:**
   - Multi-stage builds (already implemented)
   - Minimize layers
   - Use .dockerignore

4. **Monitor Resource Usage:**
   ```batch
   podman stats
   ```

## Backup Strategy

### Full System Backup

```batch
REM Backup database
podman exec yolo_postgres pg_dump -U yolo_user yolo_assembly > db_backup.sql

REM Backup volumes (requires stopping containers)
PODMAN_STOP.bat
podman volume export postgres_data > postgres_data.tar
podman volume export redis_data > redis_data.tar
podman volume export portainer_data > portainer_data.tar

REM Backup storage directory
xcopy /E /I backend\storage backup\storage

REM Start services again
PODMAN_START.bat
```

### Scheduled Backups

Create a scheduled task in Windows Task Scheduler to run backup script daily.

## Support & Resources

**Official Documentation:**
- Podman: https://podman.io/docs
- Podman Desktop: https://podman-desktop.io/
- Portainer: https://docs.portainer.io/

**Common Issues:**
1. Check logs: `PODMAN_LOGS.bat`
2. Check container status: `podman-compose ps`
3. Try restarting: `PODMAN_RESTART.bat`
4. If all fails: `PODMAN_CLEANUP.bat` then `PODMAN_START.bat`

**Get Help:**
- GitHub Issues: https://github.com/containers/podman/issues
- Community Forum: https://github.com/containers/podman/discussions
