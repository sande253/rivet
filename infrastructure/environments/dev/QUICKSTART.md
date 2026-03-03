# Rivet Terraform Quick Start

## Prerequisites Checklist

- [ ] AWS CLI configured with credentials
- [ ] Terraform >= 1.5 installed
- [ ] Anthropic API key obtained
- [ ] Bedrock model access enabled in us-east-1

## One-Time Setup (5 minutes)

```bash
# 1. Navigate to dev environment
cd infrastructure/environments/dev

# 2. Set your Anthropic API key
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"

# 3. Initialize Terraform
terraform init

# 4. Review the plan
terraform plan

# 5. Deploy infrastructure
terraform apply
# Type 'yes' when prompted
```

## Verify Deployment

```bash
# Get application URL
terraform output app_url

# Get ECR repository URL
terraform output ecr_repository_url

# Check all outputs
terraform output
```

## Deploy Application

```bash
# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push (from application directory)
cd ../../../application
docker build -t rivet-dev .
docker tag rivet-dev:latest $ECR_URL:latest
docker push $ECR_URL:latest

# Force ECS to deploy new image
aws ecs update-service \
  --cluster rivet-dev \
  --service rivet-dev-service \
  --force-new-deployment \
  --region us-east-1
```

## Access Application

```bash
# Get URL and test
APP_URL=$(cd ../../../infrastructure/environments/dev && terraform output -raw app_url)
echo "Application URL: $APP_URL"
curl $APP_URL
```

## Common Commands

```bash
# View current state
terraform state list

# Check for configuration drift
terraform plan

# Update infrastructure
terraform apply

# View logs
aws logs tail /ecs/rivet-dev --follow --region us-east-1

# Scale to 2 tasks
# Edit terraform.tfvars: desired_count = 2
terraform apply

# Stop all tasks (save costs)
# Edit terraform.tfvars: desired_count = 0
terraform apply

# Destroy everything
terraform destroy
```

## Troubleshooting

### "Error: No valid credential sources found"
```bash
aws configure
# Enter your AWS access key and secret key
```

### "Error: AccessDeniedException" (Bedrock)
- Go to AWS Console → Bedrock → Model access
- Request access to Claude and Titan models
- Wait 5-10 minutes for approval

### "Error: Secret not found"
```bash
# Ensure you exported the API key
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
terraform apply
```

### ECS task not starting
```bash
# Check logs
aws logs tail /ecs/rivet-dev --since 30m --region us-east-1

# Common fixes:
# 1. Push Docker image to ECR
# 2. Check Anthropic API key in Secrets Manager
# 3. Verify Bedrock model access
```

## What Gets Created

- **VPC**: 10.0.0.0/16 with 2 public + 2 private subnets
- **S3**: rivet-dev-uploads bucket (encrypted)
- **ECS**: Fargate cluster with 1 task (0.5 vCPU, 1GB RAM)
- **ALB**: Public load balancer on port 80
- **ECR**: Docker image repository
- **Secrets**: Anthropic API key + 4 SSM parameters
- **IAM**: Roles and policies for ECS + Bedrock
- **CloudWatch**: Logs, metrics, and alarms

**Total**: ~35-40 AWS resources

## Cost Estimate

- **Development**: ~$75-100/month + Bedrock usage
- **Bedrock**: Pay-per-use (varies by model and volume)
  - Haiku: ~$0.25 per 1M input tokens
  - Sonnet: ~$3 per 1M input tokens

## Next Steps

1. Configure custom domain with Route 53
2. Add HTTPS with ACM certificate
3. Replace SQLite with RDS PostgreSQL
4. Set up CI/CD pipeline
5. Enable auto-scaling policies
6. Add WAF for security
7. Configure backup and disaster recovery

## Support

- **Logs**: `aws logs tail /ecs/rivet-dev --follow`
- **State**: `terraform state list`
- **Outputs**: `terraform output`
- **Docs**: See README.md for detailed documentation
