# Production Deployment Guide

This guide covers deploying the Rivet application to production-grade AWS infrastructure.

## Architecture Overview

```
Internet
    ↓
CloudFront (optional)
    ↓
Application Load Balancer (HTTPS)
    ↓ (public subnets)
────────────────────────────────
    ↓ (private subnets)
EC2 Auto Scaling Group
    ↓
Docker Containers (Gunicorn)
    ↓
RDS PostgreSQL (database subnets)
    ↓
AWS Bedrock (AI)
```

## Key Production Features

✅ **Networking**
- ALB in public subnets (HTTPS with ACM certificate)
- EC2 instances in private subnets (no public IPs)
- RDS in isolated database subnets
- Multi-AZ NAT Gateways for HA
- Security groups with least-privilege access

✅ **HTTPS**
- ACM certificate with DNS validation
- HTTP → HTTPS redirect
- Modern TLS policy (TLS 1.3)

✅ **Database**
- RDS PostgreSQL 16
- Multi-AZ deployment (optional)
- Automated backups (7 days retention)
- Encrypted at rest
- Performance Insights enabled

✅ **Security**
- No SSH access to EC2 (use Systems Manager)
- IMDSv2 required
- EBS encryption
- Secrets in AWS Secrets Manager
- IAM roles (no hardcoded credentials)

✅ **High Availability**
- Min 2 instances across AZs
- Auto Scaling based on CPU and request count
- Rolling deployments (zero downtime)
- Health checks via ALB

✅ **Monitoring**
- CloudWatch Logs (30 day retention)
- CloudWatch Metrics
- ALB access logs
- RDS Performance Insights
- Custom alarms for CPU, memory, disk

✅ **Docker Production**
- Python 3.13
- Non-root user
- Gunicorn with 2 workers
- Health checks
- Optimized for t3.small

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.5
3. **AWS CLI** v2 configured
4. **Docker** installed locally
5. **Domain name** (optional, for HTTPS)

## Deployment Steps

### 1. Configure Terraform Backend

Create S3 bucket for Terraform state:

```bash
aws s3 mb s3://tf-rivet-project-bucket --region us-east-1
aws s3api put-bucket-versioning \
  --bucket tf-rivet-project-bucket \
  --versioning-configuration Status=Enabled
```

### 2. Set Up DNS (Optional - for HTTPS)

If you have a domain name:

1. Update `terraform.tfvars`:
   ```hcl
   domain_name = "app.yourdomain.com"
   ```

2. After `terraform apply`, add the DNS validation records shown in outputs

3. Point your domain to the ALB:
   ```
   app.yourdomain.com CNAME <alb-dns-name>
   ```

### 3. Configure Variables

Create `infrastructure/environments/prod/terraform.tfvars`:

```hcl
# Region
aws_region = "us-east-1"

# Networking
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-east-1a", "us-east-1b"]
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24"]
database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24"]

# SSL/TLS (optional)
domain_name = ""  # Set to your domain for HTTPS
subject_alternative_names = []

# Database
db_name              = "rivet"
db_username          = "rivetadmin"
db_instance_class    = "db.t4g.micro"
db_allocated_storage = 20
db_multi_az          = false  # Set to true for production HA
db_backup_retention_days = 7

# Compute
instance_type    = "t3.small"
container_port   = 8080
min_size         = 2
max_size         = 6
desired_capacity = 2

# GenAI
use_bedrock            = true
draft_model_id         = "anthropic.claude-3-5-sonnet-20241022-v2:0"
critic_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
vision_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
bedrock_image_model_id = "amazon.titan-image-generator-v2:0"

# Monitoring
bedrock_log_retention_days = 30
enable_bedrock_alarms      = true
```

### 4. Initialize Terraform

```bash
cd infrastructure/environments/prod
terraform init
```

### 5. Plan Deployment

```bash
terraform plan
```

Review the plan carefully. You should see:
- VPC with 6 subnets (2 public, 2 private, 2 database)
- 2 NAT Gateways (or 1 if single_nat_gateway=true)
- ALB with target group
- RDS PostgreSQL instance
- Auto Scaling Group with launch template
- Security groups
- IAM roles and policies
- CloudWatch log groups and alarms

### 6. Apply Infrastructure

```bash
terraform apply
```

This will take ~15-20 minutes (RDS creation is slow).

### 7. Build and Push Docker Image

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ecr-repository-url>

# Build production image
cd application
docker build -f Dockerfile.production -t <ecr-repository-url>:latest .

# Push to ECR
docker push <ecr-repository-url>:latest
```

### 8. Trigger Instance Refresh

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name rivet-prod-asg \
  --preferences '{
    "MinHealthyPercentage": 90,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [50, 100],
    "CheckpointDelay": 300
  }'
```

### 9. Monitor Deployment

```bash
# Check instance refresh status
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-prod-asg \
  --max-records 1

# Check application logs
aws logs tail /ec2/rivet-prod --follow

# Check instance health
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-name rivet-prod-asg \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]'
```

### 10. Verify Deployment

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Test HTTP (should redirect to HTTPS if configured)
curl -I http://<alb-dns-name>

# Test HTTPS (if configured)
curl -I https://app.yourdomain.com
```

## Post-Deployment

### Database Migration

If migrating from SQLite to PostgreSQL:

1. SSH to an EC2 instance (temporarily enable SSH in security group)
2. Export SQLite data
3. Import to PostgreSQL
4. Remove SSH access

### Monitoring Setup

1. Configure SNS topic for alarms
2. Subscribe email/SMS to SNS topic
3. Update alarm actions to use SNS topic

### Backup Verification

```bash
# List RDS snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier rivet-prod-db

# Test restore (in non-prod environment)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier rivet-test-restore \
  --db-snapshot-identifier <snapshot-id>
```

### Performance Tuning

Monitor for 1-2 weeks, then adjust:

- Auto Scaling thresholds
- RDS instance size
- EC2 instance type
- Gunicorn workers (2 × vCPU)

## Maintenance

### Update Application

```bash
# Build new image
docker build -f Dockerfile.production -t <ecr-url>:<git-sha> .
docker push <ecr-url>:<git-sha>

# Update image tag in terraform.tfvars
image_tag = "<git-sha>"

# Apply changes
terraform apply

# Trigger instance refresh
aws autoscaling start-instance-refresh --auto-scaling-group-name rivet-prod-asg
```

### Scale Up/Down

```bash
# Update terraform.tfvars
desired_capacity = 4

# Apply
terraform apply
```

### Database Maintenance

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier rivet-prod-db \
  --db-snapshot-identifier rivet-prod-manual-$(date +%Y%m%d)

# Modify instance class
aws rds modify-db-instance \
  --db-instance-identifier rivet-prod-db \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

## Troubleshooting

### Instances Not Healthy

```bash
# Check instance logs
aws logs tail /ec2/rivet-prod --since 30m

# Check container status (via Systems Manager)
aws ssm start-session --target <instance-id>
docker ps
docker logs rivet-backend
```

### Database Connection Issues

```bash
# Verify security group rules
aws ec2 describe-security-groups \
  --group-ids <rds-sg-id>

# Test connection from EC2
aws ssm start-session --target <instance-id>
psql -h <rds-endpoint> -U rivetadmin -d rivet
```

### High CPU/Memory

```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=rivet-prod-asg \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Scale up if needed
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name rivet-prod-asg \
  --desired-capacity 4
```

## Cost Optimization

### Current Costs (Estimated)

- EC2 (2 × t3.small): ~$30/month
- RDS (db.t4g.micro): ~$15/month
- NAT Gateway (2 × Multi-AZ): ~$65/month
- ALB: ~$20/month
- Data transfer: ~$10/month
- **Total: ~$140/month**

### Reduce Costs

1. **Use single NAT Gateway** (not HA):
   ```hcl
   single_nat_gateway = true  # Saves ~$32/month
   ```

2. **Use smaller RDS instance**:
   ```hcl
   db_instance_class = "db.t4g.micro"  # Already smallest
   ```

3. **Reduce min instances during off-hours**:
   ```bash
   # Schedule via Lambda or manually
   aws autoscaling update-auto-scaling-group \
     --auto-scaling-group-name rivet-prod-asg \
     --min-size 1 \
     --desired-capacity 1
   ```

4. **Use Reserved Instances** (1-year commitment):
   - Saves ~40% on EC2 and RDS

## Security Checklist

- [ ] No public IPs on EC2 instances
- [ ] No SSH access (use Systems Manager)
- [ ] IMDSv2 required
- [ ] EBS encryption enabled
- [ ] RDS encryption enabled
- [ ] Secrets in Secrets Manager
- [ ] IAM roles (no hardcoded credentials)
- [ ] Security groups follow least-privilege
- [ ] HTTPS enforced (HTTP redirects)
- [ ] Modern TLS policy
- [ ] CloudWatch logging enabled
- [ ] Automated backups configured
- [ ] Deletion protection on RDS (prod)

## Disaster Recovery

### RTO/RPO

- **RTO** (Recovery Time Objective): 30 minutes
- **RPO** (Recovery Point Objective): 5 minutes (automated backups)

### Recovery Procedure

1. **Database Failure**:
   ```bash
   # Restore from latest snapshot
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier rivet-prod-db-restored \
     --db-snapshot-identifier <latest-snapshot>
   
   # Update Terraform to use new endpoint
   # Apply changes
   ```

2. **Region Failure**:
   - Deploy to secondary region using same Terraform
   - Restore database from snapshot
   - Update DNS to point to new region

3. **Complete Infrastructure Loss**:
   ```bash
   # Restore from Terraform state
   cd infrastructure/environments/prod
   terraform init
   terraform apply
   
   # Restore database
   aws rds restore-db-instance-from-db-snapshot ...
   ```

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review Terraform outputs
3. Consult AWS documentation
4. Contact AWS Support (if Business/Enterprise plan)
