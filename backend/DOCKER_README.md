# Docker Deployment Guide

This guide explains how to deploy the VisionForge API using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- 2GB+ free disk space
- 4GB+ RAM recommended

## Quick Start

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

**IMPORTANT**: Change the `SECRET_KEY` in `.env` for production deployments!

### 2. Build and Start Services

Start all services (PostgreSQL, Redis, API, Celery worker):

```bash
docker-compose up --build
```

Or run in detached mode:

```bash
docker-compose up -d --build
```

### 3. Initialize Database

After services start, run migrations:

```bash
docker-compose exec api alembic upgrade head
```

### 4. Access Services

- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 5. Development Mode with Flower

To enable Celery monitoring with Flower:

```bash
docker-compose --profile dev up
```

- **Flower Dashboard**: http://localhost:5555

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

### Stop Services

```bash
docker-compose stop
```

### Remove Containers

```bash
docker-compose down
```

### Remove Containers and Volumes (CAUTION: Deletes all data!)

```bash
docker-compose down -v
```

### Restart a Service

```bash
docker-compose restart api
docker-compose restart celery_worker
```

### Execute Commands in Container

```bash
# Access API container shell
docker-compose exec api bash

# Run Alembic migrations
docker-compose exec api alembic upgrade head

# Access PostgreSQL
docker-compose exec postgres psql -U yolo_user -d yolo_vision_db
```

## Environment Variables

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | yolo_user |
| `POSTGRES_PASSWORD` | PostgreSQL password | yolo_password |
| `POSTGRES_DB` | PostgreSQL database name | yolo_vision_db |
| `SECRET_KEY` | JWT secret key | (CHANGE IN PRODUCTION!) |
| `DEBUG` | Debug mode | False |
| `CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |

## Service Ports

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| API | 8000 | 8000 | FastAPI application |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Message broker |
| Flower | 5555 | 5555 | Celery monitoring (dev only) |

## Volumes

Persistent data stored in Docker volumes:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistence files

Bind mounts:

- `./uploads`: User-uploaded project files
- `./datasets`: Generated synthetic datasets
- `./models`: Trained YOLO models

## Health Checks

All services have health checks configured:

- **PostgreSQL**: Checks if database is accepting connections
- **Redis**: Ping command
- **API**: HTTP GET to `/health` endpoint
- **Celery**: Celery inspect ping command

Check health status:

```bash
docker-compose ps
```

## Troubleshooting

### Services Won't Start

1. Check if ports are available:
   ```bash
   netstat -an | findstr "8000 5432 6379"
   ```

2. Check logs for errors:
   ```bash
   docker-compose logs
   ```

### Database Connection Errors

1. Ensure PostgreSQL is healthy:
   ```bash
   docker-compose ps postgres
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

### Celery Worker Not Processing Tasks

1. Check worker status:
   ```bash
   docker-compose logs celery_worker
   ```

2. Verify Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

### Permission Issues with Volumes

On Linux/Mac, you may need to fix volume permissions:

```bash
sudo chown -R $USER:$USER uploads datasets models
```

## Production Considerations

1. **Change SECRET_KEY**: Generate a strong random key
2. **Set DEBUG=False**: Disable debug mode
3. **Use Environment Variables**: Don't commit `.env` to version control
4. **Configure CORS**: Restrict CORS origins to your frontend domains
5. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Traefik)
6. **Scale Workers**: Increase Celery worker concurrency:
   ```yaml
   command: ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
   ```

7. **Database Backups**: Regularly backup PostgreSQL volume
8. **Resource Limits**: Set CPU/memory limits in docker-compose.yml
9. **Monitoring**: Use Flower or external monitoring tools

## Scaling

Scale Celery workers horizontally:

```bash
docker-compose up --scale celery_worker=3
```

## Cleanup

Remove all stopped containers, networks, and dangling images:

```bash
docker system prune -a
```

## Support

For issues or questions, refer to the main project README or API documentation at `/docs`.
