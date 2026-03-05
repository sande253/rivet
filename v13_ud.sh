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
      "AutoScalingGroupName": "${aws:AutoScalingGroupName}",
      "InstanceId": "${aws:InstanceId}",
      "InstanceType": "${aws:InstanceType}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/ec2/rivet-prod",
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
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-prod

echo "✓ ECR authentication successful"

# ── Pull Docker Image ─────────────────────────────────────────────────────────
echo "Pulling Docker image: 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-prod:7d4d5577ad461f1778ebd982e81ed8419939b4a2"
docker pull 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-prod:7d4d5577ad461f1778ebd982e81ed8419939b4a2

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
if [ -n "arn:aws:secretsmanager:us-east-1:976792586595:secret:rivet-prod/database-credentials-vTtyEG" ]; then
    echo "Retrieving database credentials from Secrets Manager..."
    DB_SECRET=$(aws secretsmanager get-secret-value \
        --secret-id arn:aws:secretsmanager:us-east-1:976792586595:secret:rivet-prod/database-credentials-vTtyEG \
        --region us-east-1 \
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
    --secret-id arn:aws:secretsmanager:us-east-1:976792586595:secret:rivet-prod/secret-key-UfocEW \
    --region us-east-1 \
    --query SecretString \
    --output text)
echo "✓ Flask secret key retrieved"

# ── Get Anthropic API Key (only if USE_BEDROCK=false) ────────────────────────
USE_BEDROCK="true"

if [ "$USE_BEDROCK" = "false" ]; then
    echo "Retrieving Anthropic API key from Secrets Manager..."
    ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value \
        --secret-id arn:aws:secretsmanager:us-east-1:976792586595:secret:rivet-prod/anthropic-api-key-vgPhtI \
        --region us-east-1 \
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
    -p 8080:8000 \
    -e FLASK_ENV=production \
    -e ENVIRONMENT=prod \
    -e SECRET_KEY="$SECRET_KEY" \
    -e AWS_REGION=us-east-1 \
    -e AWS_DEFAULT_REGION=us-east-1 \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
    -e AWS_EC2_METADATA_DISABLED=true \
    -e S3_BUCKET=rivet-prod-uploads \
    -e USE_BEDROCK="true" \
    $ANTHROPIC_ENV \
    $DB_ENV \
    -e DRAFT_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0" \
    -e CRITIC_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0" \
    -e VISION_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0" \
    -e BEDROCK_IMAGE_MODEL_ID="amazon.titan-image-generator-v2:0" \
    -e GENAI_ENABLED=true \
    -e GENAI_CACHE_TTL=300 \
    -e GENAI_FAILURE_THRESHOLD=5 \
    -e GENAI_CIRCUIT_TIMEOUT=300 \
    --log-driver=awslogs \
    --log-opt awslogs-region=us-east-1 \
    --log-opt awslogs-group=/ec2/rivet-prod \
    --log-opt awslogs-create-group=true \
    --log-opt awslogs-stream=container-{instance_id} \
    976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-prod:7d4d5577ad461f1778ebd982e81ed8419939b4a2

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
    if curl -f http://localhost:8080/ > /dev/null 2>&1; then
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
