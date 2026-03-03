# Rivet Infrastructure

Production-ready AWS infrastructure for the Rivet application with CI/CD pipeline and AWS Bedrock integration.

## Quick Links

- **Quick Start**: [../QUICKSTART_DEPLOYMENT.md](../QUICKSTART_DEPLOYMENT.md)
- **CI/CD Setup**: [CI_CD_SETUP.md](CI_CD_SETUP.md)
- **Bedrock Migration**: [BEDROCK_MIGRATION.md](BEDROCK_MIGRATION.md)
- **Full Summary**: [../DEPLOYMENT_UPGRADE_SUMMARY.md](../DEPLOYMENT_UPGRADE_SUMMARY.md)
- **IAM Policies**: [IAM_POLICIES.md](IAM_POLICIES.md)

## Architecture Overview

```
GitHub → CI/CD Pipeline → ECR → Auto Scaling Group → ALB → CloudFront
                                        ↓
                                   EC2 Instances
                                        ↓
                        ┌───────────────┼───────────────┐
                        ↓               ↓               ↓
                    Bedrock            S3          CloudWatch
                   (Claude AI)     (Uploads)         (Logs)
```

## Features

✅ **Automated CI/CD** - GitHub Actions deployment pipeline
✅ **Zero Downtime** - Rolling updates with health checks
✅ **AWS Bedrock** - Claude models via IAM role (no API keys)
✅ **Auto Scaling** - Scales based on CPU utilization
✅ **Load Balancing** - Application Load Balancer with health checks
✅ **CDN** - CloudFront for global content delivery
✅ **Monitoring** - CloudWatch logs and metrics
✅ **Security** - IAM roles, no hardcoded credentials

## Infrastructure Components

### Networking
- VPC with public and private subnets
- Internet Gateway and NAT Gateway
- Security groups with least privilege

### Compute
- Auto Scaling Group with EC2 instances
- Launch template with user data script
- Instance refresh for zero-downtime deployments

### Load Balancing
- Application Load Balancer (ALB)
- Target group with health checks
- CloudFront distribution

### Storage
- S3 bucket for uploads
- ECR repository for Docker images

### AI/ML
- AWS Bedrock for Claude models
- Amazon Titan for image generation
- CloudWatch logs for Bedrock invocations

### Secrets
- Secrets Manager for sensitive data
- SSM Parameter Store for configuration
- IAM roles for authentication

## Directory Structure

```
infrastructure/
├── environments/
│   └── dev/
│       ├── main.tf                    # Main configuration
│       ├── variables.tf               # Variable definitions
│       ├── output.tf                  # Output values
│       └── terraform.tfvars.example   # Example configuration
├── modules/
│   ├── networking/                    # VPC, subnets, security groups
│   ├── ec2/                          # Auto Scaling Group, instances
│   ├── storage/                      # S3 buckets
│   ├── secrets/                      # Secrets Manager
│   └── bedrock/                      # Bedrock configuration
├── CI_CD_SETUP.md                    # CI/CD pipeline guide
├── BEDROCK_MIGRATION.md              # Bedrock migration guide
├── IAM_POLICIES.md                   # IAM policy reference
├── github-actions-iam-policy.json    # GitHub Actions IAM policy
└── README.md                         # This file
```

## Prerequisites

- AWS CLI configured with admin access
- Terraform >= 1.5
- GitHub repository
- AWS account

## Quick Start

### 1. Enable Bedrock Models (5 minutes)

```bash
# Go to AWS Console → Bedrock → Model access
# Enable: Claude 3.5 Sonnet, Haiku, Titan Image Generator
```

### 2. Configure Terraform (5 minutes)

```bash
cd infrastructure/environments/dev
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Deploy Infrastructure (30 minutes)

```bash
terraform init
terraform plan
terraform apply
```

### 4. Set Up CI/CD (10 minutes)

Follow [CI_CD_SETUP.md](CI_CD_SETUP.md) to configure GitHub Actions.

### 5. Verify Deployment (5 minutes)

```bash
# Get ALB URL
terraform output alb_dns_name

# Test application
curl http://<ALB_DNS>/
```

## Configuration

### Terraform Variables

Key variables in `terraform.tfvars`:

```hcl
# AWS Configuration
aws_region         = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]

# Bedrock Configuration
use_bedrock            = true
draft_model_id         = "anthropic.claude-3-5-haiku-20241022-v1:0"
critic_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
bedrock_image_model_id = "amazon.titan-image-generator-v2:0"

# Instance Configuration
instance_type    = "t3.small"
min_size         = 1
max_size         = 3
desired_capacity = 1
```

See `terraform.tfvars.example` for all options.

## Deployment

### Manual Deployment

```bash
cd infrastructure/environments/dev
terraform apply
```

### Automated Deployment (CI/CD)

Push to `main` or `dev` branch:

```bash
git add .
git commit -m "Deploy changes"
git push origin main
```

GitHub Actions will automatically:
1. Build Docker image
2. Push to ECR
3. Trigger instance refresh
4. Verify deployment

## Monitoring

### CloudWatch Logs

```bash
# View application logs
aws logs tail /ec2/rivet-dev --follow

# View Bedrock logs
aws logs tail /aws/bedrock/rivet-dev --follow
```

### CloudWatch Metrics

- EC2 CPU utilization
- ALB request count
- Bedrock invocations
- GenAI latency and errors

### Cost Monitoring

```bash
# View costs by service
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Terraform apply fails | Check AWS credentials and permissions |
| Instance refresh fails | Check CloudWatch logs for errors |
| Application not responding | Verify security groups and health checks |
| Bedrock AccessDenied | Enable models in Bedrock console |
| High costs | Review CloudWatch metrics and optimize |

### Debug Commands

```bash
# Check instance status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names rivet-dev-asg

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN>

# Check Bedrock invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## Cost Estimate

### Development Environment

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| EC2 (t3.small) | 1 instance, 24/7 | ~$15 |
| ALB | 1 ALB, low traffic | ~$20 |
| ECR | 5 images, 2GB | ~$1 |
| CloudFront | 10GB transfer | ~$1 |
| S3 | 10GB storage | ~$0.25 |
| Bedrock (Haiku) | 10M tokens | ~$8 |
| Bedrock (Sonnet) | 1M tokens | ~$18 |
| **Total** | | **~$63/month** |

### Production Environment

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| EC2 (t3.medium) | 2 instances, 24/7 | ~$60 |
| ALB | 1 ALB, medium traffic | ~$30 |
| ECR | 10 images, 5GB | ~$2 |
| CloudFront | 100GB transfer | ~$8 |
| S3 | 50GB storage | ~$1.25 |
| Bedrock (Haiku) | 50M tokens | ~$40 |
| Bedrock (Sonnet) | 10M tokens | ~$180 |
| **Total** | | **~$321/month** |

## Security

### Best Practices

✅ **No hardcoded credentials** - Uses IAM roles
✅ **Least privilege** - Minimal IAM permissions
✅ **Encrypted secrets** - Secrets Manager encryption
✅ **Private subnets** - EC2 instances not publicly accessible
✅ **Security groups** - Restricted network access
✅ **CloudTrail** - Audit logging enabled
✅ **VPC Flow Logs** - Network traffic logging

### IAM Roles

- **EC2 Role**: Bedrock, S3, Secrets Manager access
- **GitHub Actions Role**: ECR, Auto Scaling access
- **Terraform Role**: Infrastructure management

See [IAM_POLICIES.md](IAM_POLICIES.md) for details.

## Maintenance

### Regular Tasks

- **Weekly**: Review CloudWatch logs for errors
- **Monthly**: Review AWS costs and optimize
- **Quarterly**: Update Terraform modules
- **Annually**: Rotate secrets and review IAM policies

### Updates

```bash
# Update Terraform modules
terraform get -update

# Update application
git push origin main  # Triggers CI/CD

# Update infrastructure
terraform apply
```

## Rollback

### Application Rollback

```bash
# Cancel instance refresh
aws autoscaling cancel-instance-refresh \
  --auto-scaling-group-name rivet-dev-asg

# Deploy previous version
git revert HEAD
git push origin main
```

### Infrastructure Rollback

```bash
# Revert Terraform changes
git revert <commit-hash>
terraform apply
```

## Support

### Documentation

- [Quick Start Guide](../QUICKSTART_DEPLOYMENT.md)
- [CI/CD Setup](CI_CD_SETUP.md)
- [Bedrock Migration](BEDROCK_MIGRATION.md)
- [IAM Policies](IAM_POLICIES.md)
- [Full Summary](../DEPLOYMENT_UPGRADE_SUMMARY.md)

### AWS Resources

- [Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Auto Scaling Documentation](https://docs.aws.amazon.com/autoscaling/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

### Contact

- DevOps Team: [Your team contact]
- AWS Support: https://console.aws.amazon.com/support/
- GitHub Issues: [Your repo issues URL]

## License

[Your license here]

## Contributors

[Your contributors here]
