# Production Readiness Checklist

This checklist ensures the Rivet application is ready for production deployment.

## ✅ Build & Deployment

- [x] **Dockerfile**: Uses Python 3.11 slim image
- [x] **Port**: Configured for port 8000 (production standard)
- [x] **Web Server**: Gunicorn with configurable workers
- [x] **Non-root User**: Runs as `appuser` (security best practice)
- [x] **Layer Caching**: Multi-stage build optimized for caching
- [x] **SQLite Support**: sys dependencies installed in Dockerfile

## ✅ Environment Configuration

- [x] **Environment-based Config**: `config.py` reads from `os.environ`
- [x] `.env.example`: Documented all required variables
- [x] **Secrets Management**: Environment variables for sensitive data
- [x] **FLASK_ENV**: Switches between development/production modes
- [x] **DEBUG Mode**: Disabled in production config

## ✅ Database (SQLite)

- [x] **Auto-initialization**: `db.create_all()` in `app.py`
- [x] **Persistent Storage**: Database path: `instance/rivet.db`
- [x] **Volume Mount**: `./instance:/app/instance` in docker-compose
- [x] **Directory Creation**: Dockerfile creates `instance/` directory
- [x] **SQLite Tools**: Installed via apt in Dockerfile

## ✅ File Management

- [x] **Upload Folder**: `static/uploads` created in Dockerfile
- [x] **Permissions**: Owned by `appuser` (non-root)
- [x] **Volume Persistence**: Mounted as volume in docker-compose
- [x] **Directory Creation**: App auto-creates on startup

## ✅ Docker Compose

- [x] **Development Config**: `docker-compose.yml` with hot-reload
- [x] **Production Config**: `docker-compose.prod.yml` with Gunicorn
- [x] **Health Checks**: Curl-based health endpoints
- [x] **Volume Mounts**: Instance and uploads directories persisted
- [x] **Port Mapping**: 8000:8000 for consistency

## ✅ Security

- [x] **SECRET_KEY**: Generated dynamically, can be overridden
- [x] **Non-root User**: Container runs as `appuser`
- [x] **No Debug in Prod**: `FLASK_DEBUG=0` in production
- [x] **Dependencies Locked**: `requirements.txt` with pinned versions
- [x] **Secrets Handling**: Environment variables (not baked in)

## ✅ Documentation

- [x] **PRODUCTION.md**: Comprehensive deployment guide
- [x] **Dockerfile Comments**: Explains each step
- [x] **.env.example**: All variables documented
- [x] **Health Check**: Configured in docker-compose

## 📋 Deployment Steps

### Local Testing
```bash
docker-compose up --build
```

### Production Simulation
```bash
docker-compose -f docker-compose.prod.yml up --build
```

### AWS ECS Deployment
See `../infrastructure/` for Terraform configuration.

## 🔍 Verification

After deployment, verify:

1. **App starts**: `docker logs rivet`
2. **Port listening**: `curl http://localhost:8000`
3. **Database created**: `ls -la instance/rivet.db`
4. **Uploads work**: Upload an image and check `static/uploads/`
5. **Health check**: `curl http://localhost:8000/`

## 📈 Performance Tuning

Gunicorn workers in Dockerfile (default: 2):
- CPU 0.25: 1–2 workers
- CPU 0.5: 2–3 workers
- CPU 1.0: 4–5 workers
- CPU 2.0: 8–10 workers

Edit Dockerfile `CMD` to adjust.

## 🚀 Next Steps

1. Set up AWS infrastructure: `cd ../infrastructure/`
2. Configure Terraform variables
3. Deploy with: `terraform apply`
4. Monitor logs in CloudWatch

---

**Last Updated**: March 1, 2026
