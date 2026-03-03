# Rivet AI Infrastructure - Deployment Summary

## Overview

This Terraform configuration implements a complete AI-powered product viability analysis platform on AWS, following the architecture specified in `plan.md.txt`.

## Architecture Components

### 1. AI/ML Layer (Bedrock Integration)
- **Draft Agent**: Claude 3.5 Haiku for fast, cost-effective tip generation
- **Critic Agent**: Claude 3.5 Sonnet for high-quality evaluation and refinement
- **Vision Agent**: Optional Claude Sonnet with Vision for image attribute extraction
- **Image Generation**: Amazon Titan for product mockup creation
- **Model Routing**: Environment-based configuration via SSM Parameter Store

### 2. Application Layer
- **ECS Fargate**: Containerized Flask application with auto-scaling capability
- **Application Load Balancer**: Public-facing HTTP endpoint (HTTPS ready)
- **ECR**: Private Docker image registry with lifecycle policies
- **Task Roles**: Least-privilege IAM with Bedrock invocation permissions

### 3. Data Layer
- **S3**: Encrypted storage for product images with versioning
- **Secrets Manager**: Secure Anthropic API key storage
- **SSM Parameter Store**: GenAI model configuration (draft, critic, vision, image models)

### 4. Networking Layer
- **VPC**: Multi-AZ deployment with public/private subnet isolation
- **NAT Gateway**: Secure outbound internet access for private subnets
- **Security Groups**: Minimal ingress rules (ALB → ECS only)

### 5. Observability Layer
- **CloudWatch Logs**: Application and Bedrock invocation logs (14-day retention)
- **CloudWatch Metrics**: Custom GenAI telemetry
  - Latency tracking (ms)
  - Error rate monitoring
  - Circuit breaker state
- **CloudWatch Alarms**: Automated alerting for performance degradation
  - High latency threshold: 5000ms
  - Error threshold: 10 errors per 5 minutes

## Key Features Implemented

### Idempotent Resource Management
- Terraform automatically checks resource existence before creation
- Updates existing resources in-place when possible
- No manual resource tracking required
- State stored remotely in S3 with encryption

### AI Agentic Loop
- **Draft → Critic → Optimizer** workflow
- Grounded prompting with market data context
- Automatic retry on low-quality scores (< 75/100)
- Rubric-based evaluation (clarity, actionability, on-brand, length)

### Safety & Reliability
- Circuit breaker pattern for GenAI failures
- Response caching to reduce costs
- Pre/post content filters (configurable)
- Graceful degradation to deterministic-only mode

### Cost Optimization
- Haiku for draft (10x cheaper than Sonnet)
- Sonnet only for critic (short outputs)
- In-memory caching (300s TTL)
- S3 lifecycle policies (30-day expiration)
- ECR image retention (5 most recent)

## Module Structure

```
infrastructure/
├── modules/
│   ├── networking/      # VPC, subnets, security groups, NAT
│   ├── storage/         # S3 buckets with encryption
│   ├── secrets/         # Secrets Manager + SSM parameters
│   ├── bedrock/         # Bedrock IAM + CloudWatch observability
│   └── compute/         # ECS, ALB, ECR, task definitions
└── environments/
    └── dev/
        ├── main.tf              # Module composition
        ├── variables.tf         # Input variables
        ├── outputs.tf           # Output values
        ├── terraform.tfvars     # Configuration values
        ├── README.md            # Detailed documentation
        ├── QUICKSTART.md        # Quick reference
        └── validate.sh          # Prerequisites checker
```

## Resource Inventory

### Networking (10 resources)
- 1 VPC
- 2 Public subnets (ALB)
- 2 Private subnets (ECS)
- 1 Internet Gateway
- 1 NAT Gateway + Elastic IP
- 2 Route tables + 4 associations
- 2 Security groups (ALB, ECS)

### Storage (4 resources)
- 1 S3 bucket
- Versioning configuration
- Encryption configuration
- Public access block

### Secrets (7 resources)
- 1 Secrets Manager secret + version
- 4 SSM parameters (draft, critic, vision, image model IDs)
- 2 IAM policies (secret read, SSM read)

### Bedrock (6+ resources)
- 1 CloudWatch log group
- 1 IAM policy (Bedrock invoke)
- 3 Metric filters (latency, errors, circuit breaker)
- 2 CloudWatch alarms (optional)

### Compute (12 resources)
- 1 ECR repository + lifecycle policy
- 1 CloudWatch log group
- 2 IAM roles (execution, task) + 5 policy attachments
- 1 ECS cluster
- 1 Task definition
- 1 Application Load Balancer
- 1 Target group
- 1 Listener
- 1 ECS service

**Total**: ~40 AWS resources

## Configuration Variables

### Required
- `aws_region`: AWS region (default: us-east-1)
- `availability_zones`: Two AZs for multi-AZ deployment
- `anthropic_api_key`: Anthropic API key (via TF_VAR_anthropic_api_key)

### Optional (with defaults)
- `draft_model_id`: Bedrock model for draft (default: Claude 3.5 Haiku)
- `critic_model_id`: Bedrock model for critic (default: Claude 3.5 Sonnet)
- `vision_model_id`: Bedrock model for vision (default: empty/disabled)
- `bedrock_image_model_id`: Bedrock model for images (default: Titan v2)
- `vpc_cidr`: VPC CIDR block (default: 10.0.0.0/16)
- `cpu`: Fargate CPU units (default: 512)
- `memory`: Fargate memory MB (default: 1024)
- `desired_count`: Number of ECS tasks (default: 1)

## Deployment Process

### Prerequisites
1. AWS CLI configured with valid credentials
2. Terraform >= 1.5 installed
3. Anthropic API key obtained
4. Bedrock model access enabled in us-east-1

### Steps
```bash
# 1. Navigate to environment
cd infrastructure/environments/dev

# 2. Validate prerequisites (Linux/Mac)
./validate.sh

# 3. Set API key
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"

# 4. Initialize
terraform init

# 5. Review plan
terraform plan

# 6. Deploy
terraform apply
```

### Post-Deployment
```bash
# Build and push Docker image
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

cd ../../../application
docker build -t rivet-dev .
docker tag rivet-dev:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Deploy to ECS
aws ecs update-service \
  --cluster rivet-dev \
  --service rivet-dev-service \
  --force-new-deployment \
  --region us-east-1
```

## Outputs

After deployment, Terraform provides:
- `app_url`: Public ALB URL
- `ecr_repository_url`: Docker image repository
- `cloudwatch_log_group`: Application logs
- `bedrock_log_group`: Bedrock invocation logs
- `s3_bucket_name`: Upload bucket name
- `vpc_id`: VPC identifier
- `anthropic_secret_name`: Secret name in Secrets Manager
- `draft_model_parameter`: SSM parameter for draft model
- `critic_model_parameter`: SSM parameter for critic model

## Security Considerations

### Implemented
- ✅ Secrets stored in AWS Secrets Manager (never in code)
- ✅ S3 encryption at rest (AES256)
- ✅ S3 public access blocked
- ✅ VPC with private subnets for ECS tasks
- ✅ Security groups with minimal ingress
- ✅ IAM roles with least-privilege policies
- ✅ CloudWatch logging enabled
- ✅ S3 versioning for data recovery

### Recommended for Production
- 🔲 Enable HTTPS with ACM certificate
- 🔲 Add WAF rules to ALB
- 🔲 Enable CloudTrail for audit logging
- 🔲 Add DynamoDB table for Terraform state locking
- 🔲 Enable MFA for AWS account
- 🔲 Implement secrets rotation
- 🔲 Add VPC Flow Logs
- 🔲 Enable GuardDuty

## Cost Estimate

### Monthly Costs (Development)
- **ECS Fargate**: $15 (0.5 vCPU, 1GB, 1 task, 24/7)
- **Application Load Balancer**: $20
- **NAT Gateway**: $35 (largest fixed cost)
- **S3**: $1 (< 100GB storage)
- **CloudWatch**: $5 (logs + metrics)
- **Secrets Manager**: $0.40 (1 secret)
- **ECR**: $0.10 (< 1GB images)

**Fixed Total**: ~$75-80/month

### Variable Costs (Usage-Based)
- **Bedrock Claude Haiku**: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- **Bedrock Claude Sonnet**: $3 per 1M input tokens, $15 per 1M output tokens
- **Bedrock Titan Image**: $0.008 per image
- **Data Transfer**: $0.09 per GB (out to internet)

**Example Usage**: 10,000 analyses/month
- Draft (Haiku): ~$5
- Critic (Sonnet): ~$10
- Total: ~$90-95/month

## Monitoring & Alerts

### CloudWatch Metrics
- `Rivet/dev/GenAILatencyMs`: Average response time
- `Rivet/dev/GenAIErrors`: Error count
- `Rivet/dev/CircuitBreakerOpen`: Circuit breaker state

### Alarms
- High latency: Triggers when avg latency > 5000ms for 10 minutes
- High error rate: Triggers when errors > 10 in 5 minutes

### Log Groups
- `/ecs/rivet-dev`: Application logs (Flask, GenAI service)
- `/aws/bedrock/rivet-dev`: Bedrock invocation logs

## Maintenance

### Regular Tasks
- Monitor CloudWatch dashboards weekly
- Review cost reports monthly
- Update Docker images as needed
- Rotate Anthropic API key quarterly
- Review security group rules quarterly

### Scaling
```hcl
# Edit terraform.tfvars
desired_count = 2  # Scale to 2 tasks
cpu = 1024         # Upgrade to 1 vCPU
memory = 2048      # Upgrade to 2GB

# Apply changes
terraform apply
```

### Model Updates
```hcl
# Edit terraform.tfvars
draft_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Upgrade

# Apply changes
terraform apply
# ECS tasks automatically restart with new model ID
```

## Disaster Recovery

### Backup Strategy
- **S3**: Versioning enabled (30-day lifecycle)
- **Secrets**: 7-day recovery window
- **Terraform State**: Stored in S3 with encryption
- **Application**: Docker images in ECR (5 most recent)

### Recovery Procedures
1. **Lost infrastructure**: `terraform apply` recreates from state
2. **Corrupted state**: Restore from S3 versioning
3. **Deleted secret**: Recover within 7 days from Secrets Manager
4. **Lost data**: Restore from S3 versions

## Troubleshooting

### Common Issues

**Bedrock Access Denied**
```bash
# Enable model access in AWS Console
# Bedrock → Model access → Request access
```

**ECS Task Fails**
```bash
# Check logs
aws logs tail /ecs/rivet-dev --since 30m --region us-east-1

# Common causes:
# - Missing Anthropic API key
# - ECR image not pushed
# - Insufficient memory/CPU
```

**High Costs**
```bash
# Check Bedrock usage
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://bedrock-filter.json

# Reduce costs:
# - Set desired_count = 0 when not in use
# - Use Haiku instead of Sonnet for draft
# - Increase cache TTL
```

## Next Steps

### Phase 1: Production Readiness
1. Add HTTPS with ACM certificate
2. Configure custom domain with Route 53
3. Replace SQLite with RDS PostgreSQL
4. Enable auto-scaling policies
5. Add DynamoDB for state locking

### Phase 2: Enhanced Features
1. Implement Admin UI for AI proposals
2. Add vision assist with image analysis
3. Enable SSE streaming for real-time tips
4. Implement A/B testing for model comparison
5. Add user authentication

### Phase 3: Operations
1. Set up CI/CD pipeline (GitHub Actions)
2. Add comprehensive monitoring dashboards
3. Implement automated backups
4. Configure multi-region deployment
5. Add disaster recovery procedures

## Assumptions

1. **Region**: us-east-1 (Bedrock model availability)
2. **Environment**: Development (single NAT, no HA)
3. **Database**: SQLite (not persistent across deployments)
4. **Protocol**: HTTP only (HTTPS requires ACM certificate)
5. **Domain**: ALB DNS name (no custom domain)
6. **Authentication**: None (add in production)
7. **Scaling**: Manual (auto-scaling not configured)
8. **Backup**: S3 versioning only (no automated snapshots)

## Support & Documentation

- **Detailed Guide**: `infrastructure/environments/dev/README.md`
- **Quick Start**: `infrastructure/environments/dev/QUICKSTART.md`
- **Validation**: `infrastructure/environments/dev/validate.sh`
- **Architecture**: `plan.md.txt`
- **Application**: `application/README.md`

## Conclusion

This Terraform configuration provides a production-ready foundation for the Rivet AI platform with:
- ✅ Complete AI agentic loop (Draft → Critic → Optimizer)
- ✅ Bedrock integration with multiple models
- ✅ Comprehensive observability
- ✅ Security best practices
- ✅ Cost optimization
- ✅ Idempotent resource management
- ✅ Environment-aware configuration

The infrastructure is ready for immediate deployment and can scale to production with the recommended enhancements.
