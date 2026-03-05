#!/bin/bash
# Production user data script for Amazon Linux 2023
# Installs Docker, authenticates to ECR, pulls image, and runs container

set -e

# Logging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "Rivet Backend Initialization (PRODUCTION)"
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

# ── Install CloudWatch Agent ──────────────────────────────────────────────────
echo "Installing CloudWatch Agent..."
curl -s -o /tmp/amazon-cloudwatch-agent.rpm https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U /tmp/amazon-cloudwatch-agent.rpm
rm -f /tmp/amazon-cloudwatch-agent.rpm

# Configure CloudWatch Agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'EOF'
{
  "metrics": {
    "namespace": "CWAgent",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          {"name": "cpu_usage_iowait", "rename": "CPU_IOWAIT", "unit": "Percent"},
          "cpu_time_guest"
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "diskio": {
        "measurement": [
          "io_time"
        ],
        "metrics_collection_interval": 60
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": [
          "tcp_established",
          "tcp_time_wait"
        ],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "AutoScalingGroupName": "$${aws:AutoScalingGroupName}",
      "InstanceId": "$${aws:InstanceId}",
      "InstanceType": "$${aws:InstanceType}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "${log_group_name}",
            "log_stream_name": "{instance_id}/user-data.log"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch Agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

echo "✓ CloudWatch Agent installed and started"

# ── Authenticate to ECR ───────────────────────────────────────────────────────
echo "Authenticating to ECR..."
aws ecr get-login-password --region ${aws_region} | \
    docker login --username AWS --password-stdin ${ecr_repository_url}

echo "✓ ECR authentication successful"

# ── Pull Docker Image ─────────────────────────────────────────────────────────
IMAGE_URI="${ecr_repository_url}:${image_tag}"
echo "Pulling Docker image: $IMAGE_URI"
docker pull "$IMAGE_URI"

echo "✓ Docker image pulled successfully"

# ── Get IAM Role Credentials (IMDSv2) ────────────────────────────────────────
echo "Retrieving IAM role credentials..."

# Fetch IMDSv2 token first (required since http_tokens = "required")
IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Get IAM role name and temporary credentials
ROLE_NAME=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
    http://169.254.169.254/latest/meta-data/iam/security-credentials/)
CREDENTIALS=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
    http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)

# Extract credentials using Python (more reliable than grep)
AWS_ACCESS_KEY_ID=$(echo "$CREDENTIALS" | python3 -c "import sys, json; print(json.load(sys.stdin)['AccessKeyId'])")
AWS_SECRET_ACCESS_KEY=$(echo "$CREDENTIALS" | python3 -c "import sys, json; print(json.load(sys.stdin)['SecretAccessKey'])")
AWS_SESSION_TOKEN=$(echo "$CREDENTIALS" | python3 -c "import sys, json; print(json.load(sys.stdin)['Token'])")

echo "Retrieved IAM role credentials"

# ── Get Database Credentials (if using RDS) ───────────────────────────────────
if [ -n "${db_secret_arn}" ]; then
    echo "Retrieving database credentials from Secrets Manager..."
    DB_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id ${db_secret_arn} \
        --region ${aws_region} \
        --query SecretString \
        --output text)
    
    DB_HOST=$(echo "$DB_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['host'])")
    DB_NAME=$(echo "$DB_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['dbname'])")
    DB_USER=$(echo "$DB_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])")
    DB_PASSWORD=$(echo "$DB_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")
    DB_PORT=$(echo "$DB_SECRET" | python3 -c "import sys, json; print(json.load(sys.stdin).get('port', '5432'))")
    
    DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    DB_ENV="-e DATABASE_URL=$DATABASE_URL"
    
    echo "✓ Database credentials retrieved"
else
    echo "No database configured (using SQLite)"
    DB_ENV=""
fi

# ── Get Flask Secret Key ─────────────────────────────────────────────────────
echo "Retrieving Flask secret key from Secrets Manager..."
SECRET_KEY=$(aws secretsmanager get-secret-value \
    --secret-id ${secret_key_arn} \
    --region ${aws_region} \
    --query SecretString \
    --output text)
echo "✓ Flask secret key retrieved"

# ── Get Anthropic API Key (only if USE_BEDROCK=false) ────────────────────────
USE_BEDROCK="${use_bedrock}"

if [ "$USE_BEDROCK" = "false" ]; then
    echo "Retrieving Anthropic API key from Secrets Manager..."
    ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value \
        --secret-id ${anthropic_secret_arn} \
        --region ${aws_region} \
        --query SecretString \
        --output text)
    echo "✓ Anthropic API key retrieved"
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
    -e FLASK_ENV=production \
    -e ENVIRONMENT=${environment} \
    -e SECRET_KEY="$SECRET_KEY" \
    -e AWS_REGION=${aws_region} \
    -e AWS_DEFAULT_REGION=${aws_region} \
    -e S3_BUCKET=${upload_bucket_name} \
    -e USE_BEDROCK="${use_bedrock}" \
    $ANTHROPIC_ENV \
    $DB_ENV \
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
    --log-opt awslogs-group=${log_group_name} \
    --log-opt awslogs-create-group=true \
    --log-opt awslogs-stream=container-{instance_id} \
    "$IMAGE_URI"

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
echo ""
echo "Container logs (last 20 lines):"
docker logs --tail 20 rivet-backend
