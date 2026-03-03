# Rivet Terraform - Quick Reference Card

## Prerequisites
```bash
# Check AWS credentials
aws sts get-caller-identity

# Set API key
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"

# Validate (Linux/Mac)
./validate.sh
```

## Deployment
```bash
cd infrastructure/environments/dev

# Initialize
terraform init

# Deploy
terraform apply
```

## Post-Deployment
```bash
# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Build and push
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

## Common Commands
```bash
# View outputs
terraform output

# View state
terraform state list

# Check drift
terraform plan

# View logs
aws logs tail /ecs/rivet-dev --follow

# Scale down (save costs)
# Edit terraform.tfvars: desired_count = 0
terraform apply

# Destroy
terraform destroy
```

## Outputs
```bash
terraform output app_url              # Application URL
terraform output ecr_repository_url   # Docker registry
terraform output s3_bucket_name       # Upload bucket
terraform output cloudwatch_log_group # App logs
terraform output bedrock_log_group    # Bedrock logs
```

## Troubleshooting
```bash
# Check ECS tasks
aws ecs list-tasks --cluster rivet-dev --region us-east-1

# View recent logs
aws logs tail /ecs/rivet-dev --since 30m --region us-east-1

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Verify secret
aws secretsmanager get-secret-value \
  --secret-id rivet-dev/anthropic-api-key \
  --region us-east-1
```

## Cost Optimization
```bash
# Stop tasks (saves ~$15/month)
# Edit terraform.tfvars: desired_count = 0
terraform apply

# Use cheaper models
# Edit terraform.tfvars:
# draft_model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
# critic_model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
terraform apply
```

## Files
- **README.md** - Complete guide
- **QUICKSTART.md** - 5-minute deployment
- **CHECKLIST.md** - Step-by-step checklist
- **terraform.tfvars** - Configuration
- **terraform.tfvars.example** - Examples
- **validate.sh** - Prerequisites check

## Resources Created
- VPC + networking (10)
- S3 bucket (4)
- Secrets + parameters (7)
- Bedrock + monitoring (6+)
- ECS + ALB (12)
**Total**: ~40 resources

## Cost Estimate
- **Fixed**: ~$75-80/month
- **Variable**: ~$15/month (10k analyses)
- **Total**: ~$90-95/month

## Support
- Logs: `aws logs tail /ecs/rivet-dev --follow`
- State: `terraform state list`
- Docs: See README.md
