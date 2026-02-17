# Docker Deployment Guide

## Quick Start

### 1. Install Docker Desktop

Download and install Docker Desktop for Windows:
- Visit: https://www.docker.com/products/docker-desktop
- Download the installer
- Run the installer
- Restart your computer if prompted

### 2. Start the Containers

Simply run:
```batch
DOCKER_START.bat
```

This will:
- Start PostgreSQL database
- Start Redis cache
- Start FastAPI backend
- Start Celery workers
- Open API documentation in browser

**All containers are configured to restart automatically on system boot!**

### 3. Stop the Containers

```batch
DOCKER_STOP.bat
```

## Available Commands

### DOCKER_START.bat
Starts all services in detached mode (runs in background).
- Containers will restart automatically on system boot
- Services continue running even after closing terminal

### DOCKER_STOP.bat
Stops all running containers gracefully.

### DOCKER_RESTART.bat
Restarts all services (useful after configuration changes).

### DOCKER_LOGS.bat
View real-time logs from all services.
- Press Ctrl+C to exit

### DOCKER_CLEANUP.bat
⚠️ **WARNING**: Removes all containers, volumes, and data!
- Use this to completely reset the system
- All database data will be lost

## Services & Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Backend API | 8002 | http://localhost:8002 | FastAPI application |
| API Docs | 8002 | http://localhost:8002/docs | Swagger UI |
| PostgreSQL | 5433 | localhost:5433 | Database |
| Redis | 6379 | localhost:6379 | Cache & message broker |

## Container Configuration

### Restart Policy: `unless-stopped`

All containers use the `unless-stopped` restart policy, which means:
- ✅ Containers start automatically on system boot
- ✅ Containers restart if they crash
- ✅ Containers remain stopped if you manually stop them
- ❌ Containers do NOT restart if Docker daemon is stopped

### Enable Docker on System Startup

**Windows:**
1. Open Docker Desktop
2. Settings → General
3. Enable "Start Docker Desktop when you log in"
4. Click "Apply & Restart"

Now the backend will start automatically whenever you boot your computer!

## Database Initialization

On first startup, the database will be automatically initialized:
1. PostgreSQL creates the database
2. Alembic runs migrations
3. Tables are created

To reset the database:
```batch
DOCKER_CLEANUP.bat
DOCKER_START.bat
```

## Volumes (Persistent Data)

The following data persists even after container restarts:

- **postgres_data**: Database files
- **redis_data**: Redis persistence
- **./backend/storage**: Uploaded files, datasets, models
- **./backend/logs**: Application logs

## Environment Variables

Configuration is managed through `docker-compose.yml`.

To change settings:
1. Edit `docker-compose.yml`
2. Find the `environment:` section
3. Modify values
4. Run `DOCKER_RESTART.bat`

### Important Settings to Change in Production:

```yaml
SECRET_KEY: "change-this-to-random-secret"
DEBUG: "False"
DATABASE_URL: "postgresql://user:pass@host/db"
```

## Troubleshooting

### Container won't start

Check logs:
```batch
DOCKER_LOGS.bat
```

Or for specific service:
```batch
docker-compose logs backend
docker-compose logs postgres
docker-compose logs redis
docker-compose logs celery_worker
```

### Port already in use

If port 8002 is already taken:
1. Edit `docker-compose.yml`
2. Change `"8002:8002"` to `"8003:8002"` (or any free port)
3. Restart: `DOCKER_RESTART.bat`

### Database connection errors

Check if PostgreSQL is healthy:
```batch
docker-compose ps
```

You should see:
```
yolo_postgres   Up (healthy)
```

### Reset everything

```batch
DOCKER_CLEANUP.bat
DOCKER_START.bat
```

## Development Workflow

### Making Code Changes

1. Edit code in `backend/` directory
2. Restart containers: `DOCKER_RESTART.bat`
3. Changes will be reflected immediately

### Adding Python Dependencies

1. Edit `backend/requirements.txt`
2. Rebuild containers:
   ```batch
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Database Migrations

Inside the backend container:
```batch
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic upgrade head
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

Then remove ports exposure for security:
- Remove `ports:` from postgres service
- Remove `ports:` from redis service
- Keep only backend port 8002 (or use reverse proxy)

## Health Checks

All services include health checks:

**Backend:**
- Endpoint: http://localhost:8002/health
- Checks every 30s
- Auto-restarts if unhealthy

**PostgreSQL:**
- Checks database connectivity
- Checks every 10s

**Redis:**
- Checks Redis PING response
- Checks every 10s

## Auto-Start on System Boot

### Current Configuration: ✅ Enabled

All containers have `restart: unless-stopped` which means:
- Containers start automatically when Docker Desktop starts
- Docker Desktop can be configured to start on login

### To Disable Auto-Start:

Edit `docker-compose.yml` and change:
```yaml
restart: unless-stopped
```
to:
```yaml
restart: "no"
```

Then restart:
```batch
DOCKER_RESTART.bat
```

## Advanced Commands

### Access backend shell:
```batch
docker-compose exec backend bash
```

### Access PostgreSQL:
```batch
docker-compose exec postgres psql -U yolo_user -d yolo_assembly
```

### Access Redis CLI:
```batch
docker-compose exec redis redis-cli
```

### View specific service logs:
```batch
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

### Scale Celery workers:
```batch
docker-compose up -d --scale celery_worker=3
```

## Monitoring

### Container Status:
```batch
docker-compose ps
```

### Resource Usage:
```batch
docker stats
```

### Disk Usage:
```batch
docker system df
```

## Backup & Restore

### Backup Database:
```batch
docker-compose exec postgres pg_dump -U yolo_user yolo_assembly > backup.sql
```

### Restore Database:
```batch
docker-compose exec -T postgres psql -U yolo_user yolo_assembly < backup.sql
```

### Backup Volumes:
```batch
docker run --rm -v yolo-computer-vision-baseline_postgres_data:/data -v %cd%:/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

## Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Use strong database password
- [ ] Set `DEBUG: "False"` in production
- [ ] Configure proper CORS origins
- [ ] Use HTTPS in production
- [ ] Don't expose database ports publicly
- [ ] Regular security updates
- [ ] Enable Docker Content Trust

## Support

If you encounter issues:
1. Check logs: `DOCKER_LOGS.bat`
2. Check container status: `docker-compose ps`
3. Try restarting: `DOCKER_RESTART.bat`
4. If all fails, cleanup and restart: `DOCKER_CLEANUP.bat` then `DOCKER_START.bat`
