# Production Deployment Guide

## Prerequisites

- Docker Engine 20.10+
- Python 3.11+ (for local development)
- Port 8000 available (or remap in docker-compose)

## Quick Start

### Development (with hot-reload)

```bash
cp .env.example .env
# Edit .env with your settings (ANTHROPIC_API_KEY, etc.)

docker-compose up --build
```

Access: http://localhost:8000

### Production Simulation

```bash
cp .env.example .env
# Edit .env with production values

docker-compose -f docker-compose.prod.yml up --build
```

## Docker Image

### Build
```bash
docker build -t rivet:latest .
```

### Run
```bash
docker run \
  --name rivet \
  -p 8000:8000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))') \
  -e ANTHROPIC_API_KEY=sk-ant-your-key \
  -e DATABASE_URL=sqlite:///instance/rivet.db \
  -v "$(pwd)/instance:/app/instance" \
  -v "$(pwd)/static/uploads:/app/static/uploads" \
  rivet:latest
```

## Configuration

All configuration is environment-based (see `.env.example`). Key variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `FLASK_ENV` | production | Set to `development` for debugging |
| `SECRET_KEY` | Random | **Required** for production; generate: `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `DATABASE_URL` | sqlite:///instance/rivet.db | Use `postgresql://...` for production scale |
| `ANTHROPIC_API_KEY` | (empty) | **Required**; get from https://console.anthropic.com |
| `UPLOAD_FOLDER` | static/uploads | Must be writable by appuser |
| `MAX_CONTENT_LENGTH_MB` | 16 | Max file size (in MB) for uploads |

## Database

### SQLite (default, single-container)
- Auto-created in `instance/rivet.db`
- Persisted via volume mount in docker-compose
- Suitable for single-instance deployments

### PostgreSQL (multi-container/cloud)
```bash
DATABASE_URL=postgresql://user:password@postgres-host:5432/rivet
```

## Performance Tuning

### Gunicorn Workers

The Dockerfile uses 2 workers by default. Tune based on task size:

| Task CPU | Task Memory | Recommended Workers |
|----------|-------------|---------------------|
| 256 (0.25) | 512 MB | 1–2 |
| 512 (0.5) | 1 GB | 2–3 |
| 1024 (1) | 2 GB | 4–5 |
| 2048 (2) | 4 GB | 8–10 |

Edit `Dockerfile` CMD to change:
```dockerfile
CMD ["gunicorn", "--workers", "4", ...]
```

## Security Checklist

- [ ] `SECRET_KEY` is set to a random 32+ character string (not the example)
- [ ] `ANTHROPIC_API_KEY` is injected at runtime (not baked into image)
- [ ] `FLASK_ENV=production` and `DEBUG=False` in production
- [ ] Container runs as non-root user (`appuser`)
- [ ] Database credentials (if using PostgreSQL) are in Secrets Manager, not in env vars
- [ ] File uploads are stored outside the app container (S3, EBS volume, etc.)
- [ ] ALB/ingress enforces HTTPS in front of the container

## Health Check

The container exposes a health endpoint for orchestrators:

```bash
curl http://localhost:8000/
```

Returns `200 OK` if healthy.

## Logs

Gunicorn logs to stdout/stderr (captured by Docker):

```bash
docker logs rivet
```

Set `FLASK_ENV=production` to suppress debug logs.

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volume
docker volume rm application_instance
```

## AWS ECS Deployment

See `../infrastructure/README.md` for Terraform-based ECS deployment.

Key differences from docker-compose:
- Environment variables injected via task definition
- Secrets (API keys) from AWS Secrets Manager
- Database URL points to RDS PostgreSQL
- File uploads → S3 bucket
- Logs → CloudWatch
