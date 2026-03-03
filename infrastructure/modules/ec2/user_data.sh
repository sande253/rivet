#!/bin/bash
# User data script for Amazon Linux 2023
# Installs Docker, authenticates to ECR, pulls image, and runs container

set -e

# Logging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "Rivet Backend Initialization"
echo "=========================================="
echo "Started at: $(date)"

# ── Install Docker ────────────────────────────────────────────────────────────
echo "Installing Docker..."
dnf update -y
dnf install -y docker

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

echo "✓ Docker installed and started"

# ── Install AWS CLI v2 (if not present) ──────────────────────────────────────
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI v2..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
    echo "✓ AWS CLI installed"
else
    echo "✓ AWS CLI already installed"
fi

# ── Authenticate to ECR ───────────────────────────────────────────────────────
echo "Authenticating to ECR..."
aws ecr get-login-password --region ${aws_region} | \
    docker login --username AWS --password-stdin ${ecr_repository_url}

echo "✓ ECR authentication successful"

# ── Pull Docker Image ─────────────────────────────────────────────────────────
echo "Pulling Docker image: ${ecr_repository_url}:${image_tag}"
docker pull ${ecr_repository_url}:${image_tag}

echo "✓ Docker image pulled successfully"

# ── Get Secrets from AWS Secrets Manager (Optional - only if USE_BEDROCK=false) ──
# When using Bedrock, no API key is needed (IAM role provides access)
USE_BEDROCK="${use_bedrock}"

if [ "$USE_BEDROCK" = "false" ]; then
    echo "Retrieving Anthropic API key from Secrets Manager..."
    ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value \
        --secret-id ${anthropic_secret_arn} \
        --region ${aws_region} \
        --query SecretString \
        --output text)
    echo "✓ Secrets retrieved"
    ANTHROPIC_ENV="-e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
else
    echo "Using AWS Bedrock (IAM role authentication)"
    ANTHROPIC_ENV=""
fi

# ── Run Docker Container ──────────────────────────────────────────────────────
echo "Starting Docker container..."

docker run -d \
    --name rivet-backend \
    --restart unless-stopped \
    -p ${container_port}:8000 \
    -e FLASK_ENV=development \
    -e ENVIRONMENT=${environment} \
    -e AWS_REGION=${aws_region} \
    -e S3_BUCKET=${upload_bucket_name} \
    -e USE_BEDROCK="${use_bedrock}" \
    $ANTHROPIC_ENV \
    -e DRAFT_MODEL_ID="${draft_model_id}" \
    -e CRITIC_MODEL_ID="${critic_model_id}" \
    -e VISION_MODEL_ID="${vision_model_id}" \
    -e BEDROCK_IMAGE_MODEL_ID="${bedrock_image_model_id}" \
    -e GENAI_ENABLED=true \
    -e GENAI_CACHE_TTL=300 \
    -e GENAI_FAILURE_THRESHOLD=5 \
    -e GENAI_CIRCUIT_TIMEOUT=300 \
    --log-driver=awslogs \
    --log-opt awslogs-region=${aws_region} \
    --log-opt awslogs-group=/ec2/rivet-${environment} \
    --log-opt awslogs-create-group=true \
    ${ecr_repository_url}:${image_tag}

echo "✓ Docker container started"

# ── Verify Container is Running ───────────────────────────────────────────────
sleep 10

if docker ps | grep -q rivet-backend; then
    echo "✓ Container is running"
    docker ps --filter name=rivet-backend
else
    echo "✗ Container failed to start"
    docker logs rivet-backend
    exit 1
fi

# ── Health Check ──────────────────────────────────────────────────────────────
echo "Waiting for application to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost:${container_port}/ > /dev/null 2>&1; then
        echo "✓ Application is healthy"
        break
    fi
    echo "Waiting for application... ($i/30)"
    sleep 10
done

echo "=========================================="
echo "Initialization Complete"
echo "=========================================="
echo "Completed at: $(date)"
echo "Container status:"
docker ps --filter name=rivet-backend
