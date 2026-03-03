# Restart Deployment - Quick Guide

## For Local Development

### Option 1: Flask Development Server

```bash
# Stop Flask (Ctrl+C or kill process)
pkill -f flask

# Navigate to application directory
cd application

# Restart Flask
flask --app src.wsgi:app run

# Or with debug mode
export FLASK_DEBUG=1
flask --app src.wsgi:app run
```

### Option 2: Docker Local

```bash
# Stop and remove container
docker stop rivet-backend
docker rm rivet-backend

# Rebuild image with changes
cd application
docker build -t rivet-backend:latest .

# Run container
docker run -d \
  --name rivet-backend \
  -p 8000:8000 \
  -e FLASK_ENV=development \
  -e USE_BEDROCK=true \
  -e AWS_REGION=us-east-1 \
  -e DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0 \
  -e CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  -e GENAI_ENABLED=true \
  -e ENVIRONMENT=local \
  rivet-backend:latest

# Check logs
docker logs rivet-backend --follow
```

## For AWS EC2 Deployment

### Option 1: Manual Restart (Quick)

```bash
# SSH into EC2 instance
ssh ec2-user@your-ec2-instance

# Pull latest code (if using git)
cd /path/to/rivet
git pull origin main

# Restart Docker container
docker stop rivet-backend
docker rm rivet-backend

# Pull latest image from ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ECR_URL>

docker pull <ECR_URL>:latest

# Run container (user data script will handle this)
# Or manually:
docker run -d \
  --name rivet-backend \
  --restart unless-stopped \
  -p 8080:8000 \
  -e FLASK_ENV=development \
  -e USE_BEDROCK=true \
  -e AWS_REGION=us-east-1 \
  -e DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0 \
  -e CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  -e GENAI_ENABLED=true \
  -e ENVIRONMENT=production \
  --log-driver=awslogs \
  --log-opt awslogs-region=us-east-1 \
  --log-opt awslogs-group=/ec2/rivet-dev \
  --log-opt awslogs-create-group=true \
  <ECR_URL>:latest

# Verify container is running
docker ps | grep rivet-backend
```

### Option 2: Build and Push New Image

```bash
# On your local machine

# 1. Build new Docker image
cd application
docker build -t rivet-backend:latest .

# 2. Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <YOUR_ECR_URL>

# 3. Tag image
docker tag rivet-backend:latest <YOUR_ECR_URL>:latest
docker tag rivet-backend:latest <YOUR_ECR_URL>:$(git rev-parse --short HEAD)

# 4. Push to ECR
docker push <YOUR_ECR_URL>:latest
docker push <YOUR_ECR_URL>:$(git rev-parse --short HEAD)

# 5. SSH into EC2 and restart
ssh ec2-user@your-ec2-instance

# Pull latest image
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <YOUR_ECR_URL>

docker pull <YOUR_ECR_URL>:latest

# Restart container
docker stop rivet-backend
docker rm rivet-backend
docker run -d --name rivet-backend --restart unless-stopped \
  -p 8080:8000 \
  -e USE_BEDROCK=true \
  -e AWS_REGION=us-east-1 \
  -e DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0 \
  -e CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  -e GENAI_ENABLED=true \
  -e ENVIRONMENT=production \
  <YOUR_ECR_URL>:latest
```

### Option 3: Trigger Auto Scaling Group Instance Refresh

```bash
# This will do a zero-downtime rolling update

# Get ASG name
ASG_NAME=$(aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?Tags[?Key=='Project' && Value=='rivet']].AutoScalingGroupName" \
  --output text)

# Start instance refresh
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name $ASG_NAME \
  --preferences '{
    "MinHealthyPercentage": 90,
    "InstanceWarmup": 300
  }'

# Monitor progress
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name $ASG_NAME \
  --max-records 1

# Wait for completion (takes ~30 minutes)
```

### Option 4: Use CI/CD Pipeline (Recommended)

```bash
# Commit and push changes
git add .
git commit -m "Update AI prompts for better user experience"
git push origin main

# GitHub Actions will automatically:
# 1. Build Docker image
# 2. Push to ECR
# 3. Trigger instance refresh
# 4. Verify deployment

# Monitor in GitHub Actions tab
# https://github.com/YOUR_ORG/YOUR_REPO/actions
```

## Verification Steps

### 1. Check Container is Running

```bash
# Local
docker ps | grep rivet

# EC2
ssh ec2-user@your-instance
docker ps | grep rivet-backend
```

### 2. Check Logs

```bash
# Local
docker logs rivet-backend --tail 100 --follow

# EC2
ssh ec2-user@your-instance
docker logs rivet-backend --tail 100 --follow

# Or CloudWatch
aws logs tail /ec2/rivet-dev --follow
```

### 3. Test Application

```bash
# Get endpoint
# Local: http://localhost:8000
# EC2: http://your-alb-dns-name

# Test health
curl http://localhost:8000/

# Test with browser
# Open http://localhost:8000 in browser
# Upload a test image
# Check if new prompts are reflected in analysis
```

### 4. Verify Changes Applied

Look for these improvements in the analysis:

✅ **No technical jargon**:
- Should NOT see: "dataset", "data points", "database"
- Should see: "market research", "customer preferences", "industry trends"

✅ **Constructive tone**:
- Should NOT see: "The design is a concept sketch rather than..."
- Should see: "This design features..." or "The design shows potential..."

✅ **Business-focused recommendations**:
- Should see specific actions with market benefits
- Should see encouraging, actionable guidance

## Troubleshooting

### Changes Not Visible

1. **Clear browser cache**:
   ```bash
   # Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   ```

2. **Verify correct container is running**:
   ```bash
   docker ps -a | grep rivet
   # Check the "Created" timestamp - should be recent
   ```

3. **Check if old container is still running**:
   ```bash
   docker ps -a
   # Stop all rivet containers
   docker stop $(docker ps -a -q --filter name=rivet)
   docker rm $(docker ps -a -q --filter name=rivet)
   ```

4. **Verify code changes are in container**:
   ```bash
   docker exec rivet-backend cat /app/src/services/claude_service.py | grep "design concept"
   # Should see the new prompt text
   ```

5. **Check environment variables**:
   ```bash
   docker exec rivet-backend env | grep -E "USE_BEDROCK|GENAI"
   ```

### Container Won't Start

1. **Check logs**:
   ```bash
   docker logs rivet-backend
   ```

2. **Check for port conflicts**:
   ```bash
   netstat -an | grep 8000
   # Or
   lsof -i :8000
   ```

3. **Verify image exists**:
   ```bash
   docker images | grep rivet
   ```

4. **Try running interactively**:
   ```bash
   docker run -it --rm rivet-backend:latest bash
   # Then manually start Flask to see errors
   flask --app src.wsgi:app run
   ```

## Quick Commands Reference

```bash
# Stop everything
docker stop rivet-backend && docker rm rivet-backend

# Rebuild and restart (local)
cd application && docker build -t rivet-backend:latest . && \
docker run -d --name rivet-backend -p 8000:8000 \
  -e USE_BEDROCK=true -e AWS_REGION=us-east-1 \
  rivet-backend:latest

# Check logs
docker logs rivet-backend --tail 50 --follow

# Test endpoint
curl http://localhost:8000/

# SSH to EC2 and restart
ssh ec2-user@your-instance
docker restart rivet-backend
```

## Expected Timeline

- **Local restart**: 10-30 seconds
- **Docker rebuild**: 2-5 minutes
- **ECR push + EC2 restart**: 5-10 minutes
- **Auto Scaling Group refresh**: 25-40 minutes
- **CI/CD pipeline**: 30-45 minutes

## Next Steps

After restart:

1. ✅ Test with a sample image upload
2. ✅ Verify new prompt language in analysis
3. ✅ Check that recommendations are constructive
4. ✅ Confirm no technical jargon appears
5. ✅ Monitor logs for any errors

## Support

If issues persist:

1. Check [TROUBLESHOOTING_ANALYSIS_ERROR.md](TROUBLESHOOTING_ANALYSIS_ERROR.md)
2. Review [DEBUG_QUICK_REFERENCE.md](DEBUG_QUICK_REFERENCE.md)
3. Check Docker logs for detailed errors
4. Verify environment variables are set correctly
