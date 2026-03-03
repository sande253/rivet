# Rivet Development Environment - Terraform Configuration

This directory contains Terraform configuration for deploying the Rivet AI-powered product viability analyzer to AWS in the development environment.

## Architecture Overview

The infrastructure implements an agentic AI system with the following components:

### Core Services
- **ECS Fargate**: Containerized Flask application with auto-scaling
- **Application Load Balancer**: Public-facing HTTPS endpoint
- **VPC**: Multi-AZ networking with public/private subnets
- **S3**: Encrypted storage for product images and mockups
- **ECR**: Docker image registry

### AI/ML Components
- **Amazon Bedrock**: Foundation model access for:
  - Draft agent (Claude Haiku): Fast, cost-effective tip generation
  - Critic agent (Claude Sonnet): High-quality evaluation and refinement
  - Vision agent (optional): Image attribute extraction
  - Image generation (Titan): Product mockup creation
- **AWS Secrets Manager**: Secure storage for Anthropic API keys
- **AWS Systems Manager Parameter Store**: GenAI model configuration

### Observability
- **CloudWatch Logs**: Application and Bedrock invocation logs
- **CloudWatch Metrics**: Custom GenAI telemetry (latency, errors, circuit breaker)
- **CloudWatch Alarms**: Automated alerting for performance degradation

## Prerequisites

1. **AWS CLI** configured with valid credentials
   ```bash
   aws configure
   # Ensure you have access to us-east-1 region
   aws sts get-caller-identity
   ```

2. **Terraform** >= 1.5 installed
   ```bash
   terraform version
   ```

3. **Anthropic API Key** for Claude models
   - Sign up at https://console.anthropic.com/
   - Generate an API key
   - Export as environment variable:
     ```bash
     export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
     ```

4. **Bedrock Model Access** enabled in us-east-1
   - Navigate to AWS Console → Bedrock → Model access
   - Request access to:
     - Anthropic Claude 3.5 Haiku
     - Anthropic Claude 3.5 Sonnet
     - Amazon Titan Image Generator v2 (optional)

## Directory Structure

```
infrastructure/environments/dev/
├── main.tf              # Main configuration with module composition
├── variables.tf         # Input variable definitions
├── outputs.tf           # Output value definitions
├── terraform.tfvars     # Variable values (customize this)
├── README.md           # This file
└── .terraform/         # Terraform state and plugins (auto-generated)

infrastructure/modules/
├── networking/         # VPC, subnets, security groups
├── storage/           # S3 buckets with encryption
├── secrets/           # Secrets Manager + SSM parameters
├── bedrock/           # Bedrock IAM policies + CloudWatch
└── compute/           # ECS, ALB, ECR, task definitions
```

## Configuration

### Required Variables

Edit `terraform.tfvars` to customize:

```hcl
# Core
aws_region         = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]

# GenAI Models (Bedrock model IDs)
draft_model_id  = "anthropic.claude-3-5-haiku-20241022-v1:0"
critic_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
vision_model_id = ""  # Leave empty to disable vision assist

# Container
cpu           = 512   # 0.5 vCPU
memory        = 1024  # 1 GB
desired_count = 1     # Number of tasks
```

### Sensitive Variables

Never commit secrets to version control. Supply via environment variables:

```bash
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd infrastructure/environments/dev
terraform init
```

This will:
- Download required providers (AWS ~> 5.0)
- Initialize the S3 backend for remote state
- Set up module dependencies

### 2. Review the Plan

```bash
terraform plan
```

Expected resources to be created:
- **Networking**: VPC, 2 public subnets, 2 private subnets, IGW, NAT gateway, route tables, security groups
- **Storage**: S3 bucket with versioning and encryption
- **Secrets**: Secrets Manager secret, 4 SSM parameters
- **Bedrock**: IAM policies, CloudWatch log group, metric filters, alarms
- **Compute**: ECR repository, ECS cluster, task definition, service, ALB, target group

Total: ~35-40 resources

### 3. Apply the Configuration

```bash
terraform apply
```

Review the plan and type `yes` to proceed. This will take 5-10 minutes.

### 4. Verify Deployment

```bash
# Get outputs
terraform output

# Check key resources
terraform output app_url
terraform output ecr_repository_url
terraform output s3_bucket_name
```

## Resource Management

### Idempotency

Terraform automatically handles resource state:
- **Existing resources**: Terraform imports and manages them
- **Configuration drift**: `terraform plan` detects changes
- **Updates**: `terraform apply` reconciles differences
- **No recreation**: Resources are updated in-place when possible

### State Management

State is stored remotely in S3:
- **Bucket**: `tf-rivet-project-bucket`
- **Key**: `tf-state/terraform.tfstate`
- **Encryption**: Enabled
- **Locking**: Optional DynamoDB table (commented out)

### Checking Resource Existence

Terraform automatically checks if resources exist:

```bash
# Show current state
terraform state list

# Show specific resource details
terraform state show module.storage.aws_s3_bucket.uploads

# Refresh state from AWS
terraform refresh
```

## Post-Deployment

### 1. Build and Push Docker Image

```bash
# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)

# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push (from application directory)
cd ../../../application
docker build -t rivet-dev .
docker tag rivet-dev:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### 2. Update ECS Service

```bash
# Force new deployment with latest image
aws ecs update-service \
  --cluster rivet-dev \
  --service rivet-dev-service \
  --force-new-deployment \
  --region us-east-1
```

### 3. Access the Application

```bash
# Get ALB URL
terraform output app_url

# Test endpoint
curl $(terraform output -raw app_url)
```

### 4. Monitor Logs

```bash
# Application logs
aws logs tail /ecs/rivet-dev --follow --region us-east-1

# Bedrock logs
aws logs tail /aws/bedrock/rivet-dev --follow --region us-east-1
```

## Updating Configuration

### Change Model IDs

Edit `terraform.tfvars`:
```hcl
draft_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Upgrade to Sonnet
```

Apply changes:
```bash
terraform apply
```

ECS tasks will automatically restart with new environment variables.

### Scale Up/Down

```hcl
desired_count = 2  # Run 2 tasks
cpu           = 1024  # 1 vCPU
memory        = 2048  # 2 GB
```

```bash
terraform apply
```

### Enable Vision Assist

```hcl
vision_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

```bash
terraform apply
```

## Cost Optimization

### Development Environment
- **ECS Fargate**: ~$15/month (0.5 vCPU, 1GB, 1 task)
- **ALB**: ~$20/month
- **NAT Gateway**: ~$35/month (largest cost)
- **S3**: ~$1/month (< 100GB)
- **Bedrock**: Pay-per-use (varies by usage)
- **CloudWatch**: ~$5/month

**Total**: ~$75-100/month + Bedrock usage

### Cost Reduction Tips
1. Stop ECS service when not in use: `desired_count = 0`
2. Use Haiku for draft (10x cheaper than Sonnet)
3. Enable caching to reduce Bedrock calls
4. Set S3 lifecycle policies (already configured: 30-day expiration)

## Troubleshooting

### Bedrock Access Denied

**Error**: `AccessDeniedException: Could not access model`

**Solution**: Enable model access in AWS Console
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1 \
  --query 'modelSummaries[?contains(modelId, `claude`)].modelId'
```

### ECS Task Fails to Start

**Check logs**:
```bash
aws logs tail /ecs/rivet-dev --since 10m --region us-east-1
```

**Common issues**:
- Missing Anthropic API key in Secrets Manager
- ECR image not pushed
- Insufficient memory/CPU

### State Lock Error

**Error**: `Error acquiring the state lock`

**Solution**: Wait for other operations to complete, or force unlock:
```bash
terraform force-unlock <LOCK_ID>
```

## Cleanup

To destroy all resources:

```bash
# Review what will be deleted
terraform plan -destroy

# Destroy infrastructure
terraform destroy
```

**Warning**: This will delete:
- All ECS tasks and services
- ALB and target groups
- S3 bucket (if empty)
- Secrets Manager secrets (7-day recovery window)
- VPC and networking components

## Security Best Practices

1. **Never commit secrets**: Use environment variables or AWS Secrets Manager
2. **Enable MFA**: For AWS account access
3. **Restrict IAM permissions**: Follow principle of least privilege
4. **Enable CloudTrail**: Audit all API calls
5. **Use HTTPS**: Configure ACM certificate for ALB (not included in dev)
6. **Rotate secrets**: Update Anthropic API key periodically
7. **Review security groups**: Ensure minimal ingress rules

## Next Steps

1. **Enable HTTPS**: Add ACM certificate and HTTPS listener
2. **Add RDS**: Replace SQLite with PostgreSQL for production
3. **Enable Auto Scaling**: Add target tracking policies
4. **Add WAF**: Protect ALB from common attacks
5. **Set up CI/CD**: Automate Docker builds and deployments
6. **Add DynamoDB**: Enable Terraform state locking
7. **Multi-region**: Deploy to additional regions for HA

## Support

For issues or questions:
- Check AWS CloudWatch logs
- Review Terraform plan output
- Consult AWS Bedrock documentation
- Check application logs in ECS

## Assumptions Made

1. **Region**: us-east-1 (Bedrock availability)
2. **Networking**: Single NAT gateway (dev only, not HA)
3. **Database**: SQLite in container (not persistent across deployments)
4. **HTTPS**: Not configured (HTTP only for dev)
5. **Domain**: Using ALB DNS name (no custom domain)
6. **Monitoring**: Basic CloudWatch (no third-party APM)
7. **Backup**: S3 versioning enabled, no automated backups for ECS
8. **Secrets**: Anthropic API key only (no other integrations)
