FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a separate layer for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/       ./src/
COPY static/    ./static/
COPY templates/ ./templates/

# Create data and upload directories
RUN mkdir -p static/uploads instance

# Run as non-root for security
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose production port
EXPOSE 8000

# Environment defaults (can be overridden at runtime)
ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# 2 workers handles typical task sizing (0.25–1 vCPU)
# Increase --workers for larger deployments (4+ vCPU: 4-8 workers)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "src.wsgi:app"]
