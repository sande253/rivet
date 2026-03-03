# Deploy Rivet on EC2 - Step by Step Guide

## Overview

This guide deploys your Flask application on EC2 with Auto Scaling, replacing the current ECS deployment.

**Architecture:**
- EC2 instances in Auto Scaling Group (1-3 instances)
- Application Load Balancer
- Docker containers on Amazon Linux 2023
- Gunicorn with Uvicorn workers
- IAM roles (no hardcoded credentials)
- CloudWatch monitoring

---

## Prerequisites

✅ Already completed from previous deployment:
- AWS credentials configured
- Terraform installed
- Anthropic API key set
- VPC, S3, Secrets Manager deployed
- IAM permissions configured

---

## Step 1: Build New Docker Image

The new Dockerfile uses Gunicorn with Uvicorn workers for better ASGI support.

```powershell
cd application

# Build with production Dockerfile
docker build -t rivet-dev -f Dockerfile.production .
```

**Expected output:**
```
Successfully built xxxxx
Successfully tagged rivet-dev:latest
```

---

## Step 2: Push Image to ECR

```powershell
# Get ECR URL (from previous deployment)
$ECR_URL = "976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev"

# Login to ECR
aws ecr get-login-password --region us-east-1 | `
  docker login --username AWS --password-stdin $ECR_URL

# Tag image
docker tag rivet-dev:latest ${ECR_URL}:latest

# Push to ECR
docker push ${ECR_URL}:latest
```

**Expected output:**
```
The push refers to repository [976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev]
latest: digest: sha256:xxxxx size: xxxx
```

---

## Step 3: Backup Current Configuration

```powershell
cd ..\infrastructure\environments\dev

# Backup current main.tf (ECS version)
Copy-Item main.tf main-ecs-backup.tf

# Use new EC2 configuration
Copy-Item main-ec2.tf main.tf
```

---

## Step 4: Initialize New Modules

```powershell
# Initialize EC2 module
terraform init -upgrade
```

**Expected output:**
```
Initializing modules...
- ec2 in ../../modules/ec2

Terraform has been successfully initialized!
```

---

## Step 5: Review Changes

```powershell
terraform plan
```

**What you'll see:**
- **Destroy**: ECS cluster, tasks, services (~12 resources)
- **Create**: EC2 Auto Scaling Group, Launch Template, IAM roles (~15 resources)
- **Modify**: ALB target group (change from IP to instance targets)

**Total changes**: ~27 resources

---

## Step 6: Deploy EC2 Infrastructure

```powershell
# Apply changes
terraform apply
```

Type `yes` when prompted.

**Deployment time**: 5-8 minutes

**What happens:**
1. Creates EC2 launch template
2. Creates Auto Scaling Group
3. Launches EC2 instance
4. Instance runs user data script:
   - Installs Docker
   - Authenticates to ECR
   - Pulls your image
   - Retrieves secrets
   - Starts container
5. Registers with ALB
6. Health checks pass
7. Destroys old ECS resources

---

## Step 7: Verify Deployment

### Check Auto Scaling Group
```powershell
aws autoscaling describe-auto-scaling-groups `
  --auto-scaling-group-names rivet-dev-asg `
  --region us-east-1 `
  --query 'AutoScalingGroups[0].{Desired:DesiredCapacity,Current:Instances[0].HealthStatus}'
```

### Check EC2 Instances
```powershell
aws ec2 describe-instances `
  --filters "Name=tag:Project,Values=rivet" "Name=instance-state-name,Values=running" `
  --region us-east-1 `
  --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,IP:PrivateIpAddress}'
```

### Check Target Health
```powershell
# Get target group ARN
$TG_ARN = terraform output -raw target_group_arn

# Check health
aws elbv2 describe-target-health `
  --target-group-arn $TG_ARN `
  --region us-east-1
```

**Expected**: `TargetHealth.State: "healthy"`

### Test Application
```powershell
# Get application URL
$APP_URL = terraform output -raw app_url

# Test endpoint
curl $APP_URL

# Or open in browser
start $APP_URL
```

---

## Step 8: View Logs

### Application Logs (from Docker container)
```powershell
aws logs tail /ec2/rivet-dev --follow --region us-east-1
```

### User Data Logs (instance bootstrap)
```powershell
# Get instance ID
$INSTANCE_ID = (aws ec2 describe-instances `
  --filters "Name=tag:Project,Values=rivet" "Name=instance-state-name,Values=running" `
  --region us-east-1 `
  --query 'Reservations[0].Instances[0].InstanceId' `
  --output text)

# Start SSM session
aws ssm start-session --target $INSTANCE_ID --region us-east-1

# Inside the session:
sudo cat /var/log/user-data.log
```

---

## Troubleshooting

### Issue: Instance not healthy

**Check user data logs:**
```powershell
# Via SSM Session Manager
aws ssm start-session --target <instance-id>
sudo cat /var/log/user-data.log
```

**Common causes:**
- Docker image not in ECR
- Secrets not accessible
- Container failed to start
- Health check path incorrect

### Issue: Container won't start

**Check Docker logs:**
```powershell
# Via SSM
aws ssm start-session --target <instance-id>
sudo docker logs rivet-backend
```

### Issue: Can't access application

**Check security groups:**
```powershell
# Verify ALB can reach EC2
aws ec2 describe-security-groups `
  --filters "Name=tag:Project,Values=rivet" `
  --region us-east-1
```

**Check target group:**
```powershell
aws elbv2 describe-target-health --target-group-arn <arn>
```

---

## Scaling

### Manual Scaling
```powershell
# Edit terraform.tfvars
# Change: desired_capacity = 2

terraform apply
```

### Auto Scaling (Already Configured)
- **Scale Up**: CPU > 70% for 10 minutes
- **Scale Down**: CPU < 30% for 10 minutes
- **Min**: 1 instance
- **Max**: 3 instances

---

## Cost Comparison

### ECS Fargate (Previous)
- **Cost**: ~$15/month (0.5 vCPU, 1GB, 1 task)

### EC2 t3.small (New)
- **Instance**: ~$15/month (2 vCPU, 2GB, 1 instance)
- **EBS**: ~$2/month (20GB)
- **Total**: ~$17/month

**Difference**: +$2/month, but you get:
- ✅ More CPU (2 vCPU vs 0.5)
- ✅ More memory (2GB vs 1GB)
- ✅ Better performance
- ✅ Easier debugging

---

## Rollback (If Needed)

If something goes wrong, you can rollback to ECS:

```powershell
# Restore ECS configuration
Copy-Item main-ecs-backup.tf main.tf

# Reinitialize
terraform init -upgrade

# Apply
terraform apply
```

---

## Post-Deployment Tasks

### 1. Enable Metric Filters (Optional)
```powershell
# Edit main.tf line ~86
# Change: create_metric_filters = true

terraform apply
```

### 2. Add HTTPS (Recommended for Production)
- Request ACM certificate
- Add HTTPS listener to ALB
- Redirect HTTP to HTTPS

### 3. Configure Auto Scaling Policies
- Adjust CPU thresholds
- Add memory-based scaling
- Configure scheduled scaling

### 4. Set Up Monitoring
- Create CloudWatch dashboard
- Configure SNS alerts
- Set up log insights queries

---

## Verification Checklist

- [ ] Docker image built successfully
- [ ] Image pushed to ECR
- [ ] Terraform apply completed without errors
- [ ] Auto Scaling Group created
- [ ] EC2 instance running
- [ ] Container started on instance
- [ ] Target health is "healthy"
- [ ] Application accessible via ALB URL
- [ ] Can upload and analyze products
- [ ] GenAI tips appear in results
- [ ] Logs visible in CloudWatch

---

## Success Criteria

✅ **Deployment successful when:**
1. `terraform apply` completes without errors
2. EC2 instance is running
3. Target health shows "healthy"
4. Application responds at ALB URL
5. Product analysis works end-to-end
6. No errors in CloudWatch logs

---

## Next Steps

1. **Test thoroughly** - Upload products, verify AI analysis
2. **Monitor costs** - Check AWS Cost Explorer
3. **Optimize** - Adjust instance size if needed
4. **Secure** - Add HTTPS, configure WAF
5. **Scale** - Test auto-scaling behavior

---

## Quick Commands Reference

```powershell
# Build and push
docker build -t rivet-dev -f Dockerfile.production .
docker tag rivet-dev:latest 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev:latest
docker push 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev:latest

# Deploy
cd infrastructure\environments\dev
Copy-Item main-ec2.tf main.tf
terraform init -upgrade
terraform apply

# Verify
terraform output app_url
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names rivet-dev-asg
aws logs tail /ec2/rivet-dev --follow

# Rollback
Copy-Item main-ecs-backup.tf main.tf
terraform apply
```

---

**Ready to deploy? Start with Step 1!**
