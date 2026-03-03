# Rivet Terraform Deployment Checklist

Use this checklist to ensure a smooth deployment.

## Pre-Deployment Checklist

### AWS Account Setup
- [ ] AWS account created and accessible
- [ ] AWS CLI installed and configured
  ```bash
  aws --version
  aws configure
  ```
- [ ] AWS credentials have necessary permissions:
  - [ ] EC2 (VPC, subnets, security groups)
  - [ ] ECS (clusters, services, tasks)
  - [ ] S3 (bucket creation and management)
  - [ ] IAM (roles and policies)
  - [ ] Secrets Manager
  - [ ] Systems Manager (Parameter Store)
  - [ ] Bedrock (model invocation)
  - [ ] CloudWatch (logs, metrics, alarms)
  - [ ] ECR (repository management)
- [ ] AWS region set to us-east-1
  ```bash
  aws configure get region
  ```

### Bedrock Setup
- [ ] Navigate to AWS Console → Bedrock → Model access
- [ ] Request access to required models:
  - [ ] Anthropic Claude 3.5 Haiku
  - [ ] Anthropic Claude 3.5 Sonnet
  - [ ] Amazon Titan Image Generator v2 (optional)
- [ ] Wait for approval (usually 5-10 minutes)
- [ ] Verify access:
  ```bash
  aws bedrock list-foundation-models --region us-east-1 \
    --query 'modelSummaries[?contains(modelId, `claude`)].modelId'
  ```

### Anthropic API Key
- [ ] Sign up at https://console.anthropic.com/
- [ ] Generate API key
- [ ] Export as environment variable:
  ```bash
  export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
  ```
- [ ] Verify it's set:
  ```bash
  echo $TF_VAR_anthropic_api_key
  ```

### Terraform Setup
- [ ] Terraform >= 1.5 installed
  ```bash
  terraform version
  ```
- [ ] Navigate to dev environment:
  ```bash
  cd infrastructure/environments/dev
  ```
- [ ] Review and customize `terraform.tfvars`:
  - [ ] AWS region and availability zones
  - [ ] VPC CIDR blocks
  - [ ] Model IDs (draft, critic, vision, image)
  - [ ] Container resources (CPU, memory)
  - [ ] Desired task count

### Optional Tools
- [ ] Docker installed (for building application image)
  ```bash
  docker --version
  ```
- [ ] Git installed (for version control)
  ```bash
  git --version
  ```

## Deployment Checklist

### Step 1: Validation
- [ ] Run validation script (Linux/Mac):
  ```bash
  ./validate.sh
  ```
- [ ] Or manually verify:
  - [ ] AWS CLI works: `aws sts get-caller-identity`
  - [ ] Terraform works: `terraform version`
  - [ ] API key set: `echo $TF_VAR_anthropic_api_key`
  - [ ] Bedrock access: `aws bedrock list-foundation-models --region us-east-1`

### Step 2: Initialize Terraform
- [ ] Initialize Terraform:
  ```bash
  terraform init
  ```
- [ ] Verify initialization:
  - [ ] Providers downloaded (AWS ~> 5.0)
  - [ ] Backend configured (S3)
  - [ ] Modules loaded (networking, storage, secrets, bedrock, compute)

### Step 3: Review Plan
- [ ] Generate execution plan:
  ```bash
  terraform plan
  ```
- [ ] Review resources to be created (~40 resources):
  - [ ] VPC and networking (10 resources)
  - [ ] S3 bucket (4 resources)
  - [ ] Secrets and parameters (7 resources)
  - [ ] Bedrock IAM and monitoring (6+ resources)
  - [ ] ECS and ALB (12 resources)
- [ ] Verify no unexpected changes
- [ ] Check estimated costs

### Step 4: Apply Configuration
- [ ] Apply Terraform configuration:
  ```bash
  terraform apply
  ```
- [ ] Review plan one more time
- [ ] Type `yes` to confirm
- [ ] Wait for completion (5-10 minutes)
- [ ] Verify no errors in output

### Step 5: Verify Deployment
- [ ] Check Terraform outputs:
  ```bash
  terraform output
  ```
- [ ] Save important outputs:
  - [ ] `app_url`: ___________________________
  - [ ] `ecr_repository_url`: ___________________________
  - [ ] `s3_bucket_name`: ___________________________
- [ ] Verify resources in AWS Console:
  - [ ] VPC created
  - [ ] ECS cluster created
  - [ ] ALB created
  - [ ] S3 bucket created
  - [ ] Secrets Manager secret created

## Post-Deployment Checklist

### Step 6: Build and Push Docker Image
- [ ] Get ECR repository URL:
  ```bash
  ECR_URL=$(terraform output -raw ecr_repository_url)
  echo $ECR_URL
  ```
- [ ] Authenticate Docker to ECR:
  ```bash
  aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $ECR_URL
  ```
- [ ] Navigate to application directory:
  ```bash
  cd ../../../application
  ```
- [ ] Build Docker image:
  ```bash
  docker build -t rivet-dev .
  ```
- [ ] Tag image:
  ```bash
  docker tag rivet-dev:latest $ECR_URL:latest
  ```
- [ ] Push to ECR:
  ```bash
  docker push $ECR_URL:latest
  ```
- [ ] Verify image in ECR:
  ```bash
  aws ecr describe-images --repository-name rivet-dev --region us-east-1
  ```

### Step 7: Deploy Application
- [ ] Force ECS service to deploy new image:
  ```bash
  aws ecs update-service \
    --cluster rivet-dev \
    --service rivet-dev-service \
    --force-new-deployment \
    --region us-east-1
  ```
- [ ] Wait for deployment (2-5 minutes)
- [ ] Check service status:
  ```bash
  aws ecs describe-services \
    --cluster rivet-dev \
    --services rivet-dev-service \
    --region us-east-1 \
    --query 'services[0].deployments'
  ```
- [ ] Verify task is running:
  ```bash
  aws ecs list-tasks \
    --cluster rivet-dev \
    --service-name rivet-dev-service \
    --region us-east-1
  ```

### Step 8: Test Application
- [ ] Get application URL:
  ```bash
  APP_URL=$(cd ../infrastructure/environments/dev && terraform output -raw app_url)
  echo $APP_URL
  ```
- [ ] Test health endpoint:
  ```bash
  curl $APP_URL
  ```
- [ ] Open in browser: ___________________________
- [ ] Test product analysis:
  - [ ] Upload product image
  - [ ] Verify analysis results
  - [ ] Check GenAI tips appear
- [ ] Test admin panel (if applicable)

### Step 9: Verify Monitoring
- [ ] Check CloudWatch logs:
  ```bash
  aws logs tail /ecs/rivet-dev --follow --region us-east-1
  ```
- [ ] Verify no errors in logs
- [ ] Check Bedrock logs:
  ```bash
  aws logs tail /aws/bedrock/rivet-dev --follow --region us-east-1
  ```
- [ ] Verify metrics in CloudWatch:
  - [ ] Navigate to CloudWatch → Metrics → Rivet/dev
  - [ ] Check GenAILatencyMs metric
  - [ ] Check GenAIErrors metric
- [ ] Verify alarms configured:
  - [ ] rivet-dev-genai-high-latency
  - [ ] rivet-dev-genai-error-rate

### Step 10: Security Review
- [ ] Verify S3 bucket is private:
  ```bash
  aws s3api get-public-access-block \
    --bucket rivet-dev-uploads \
    --region us-east-1
  ```
- [ ] Verify secrets are encrypted:
  ```bash
  aws secretsmanager describe-secret \
    --secret-id rivet-dev/anthropic-api-key \
    --region us-east-1
  ```
- [ ] Review security groups:
  ```bash
  aws ec2 describe-security-groups \
    --filters "Name=tag:Project,Values=rivet" \
    --region us-east-1
  ```
- [ ] Verify IAM roles have least privilege
- [ ] Check CloudTrail is enabled (optional)

## Maintenance Checklist

### Daily
- [ ] Monitor CloudWatch alarms
- [ ] Check for any failed ECS tasks

### Weekly
- [ ] Review CloudWatch logs for errors
- [ ] Check Bedrock usage and costs
- [ ] Verify application performance

### Monthly
- [ ] Review AWS cost reports
- [ ] Update Docker images if needed
- [ ] Review and update model IDs if new versions available
- [ ] Check for Terraform updates

### Quarterly
- [ ] Rotate Anthropic API key
- [ ] Review and update security groups
- [ ] Audit IAM permissions
- [ ] Review and optimize costs

## Troubleshooting Checklist

### Issue: Terraform Apply Fails
- [ ] Check AWS credentials: `aws sts get-caller-identity`
- [ ] Verify API key is set: `echo $TF_VAR_anthropic_api_key`
- [ ] Check Terraform version: `terraform version`
- [ ] Review error message in output
- [ ] Check AWS service quotas
- [ ] Verify region has Bedrock access

### Issue: ECS Task Won't Start
- [ ] Check CloudWatch logs: `aws logs tail /ecs/rivet-dev --since 30m`
- [ ] Verify Docker image exists in ECR
- [ ] Check task definition environment variables
- [ ] Verify Anthropic API key in Secrets Manager
- [ ] Check task IAM role permissions
- [ ] Verify sufficient CPU/memory allocated

### Issue: Bedrock Access Denied
- [ ] Verify model access enabled in AWS Console
- [ ] Check IAM role has bedrock:InvokeModel permission
- [ ] Verify correct model ID in SSM parameters
- [ ] Check region is us-east-1
- [ ] Wait 10 minutes after requesting access

### Issue: High Costs
- [ ] Check Bedrock usage in Cost Explorer
- [ ] Review CloudWatch logs for excessive calls
- [ ] Verify caching is enabled (GENAI_CACHE_TTL=300)
- [ ] Consider using Haiku instead of Sonnet
- [ ] Scale down ECS tasks when not in use (desired_count=0)

### Issue: Application Not Accessible
- [ ] Verify ALB is healthy: Check target group health
- [ ] Check security group allows port 80 ingress
- [ ] Verify ECS tasks are running
- [ ] Check ALB listener configuration
- [ ] Test from within VPC if external access fails

## Rollback Checklist

### If Deployment Fails
- [ ] Review error messages
- [ ] Check Terraform state: `terraform state list`
- [ ] Attempt to fix and reapply
- [ ] If unfixable, destroy and start over:
  ```bash
  terraform destroy
  terraform apply
  ```

### If Application Has Issues
- [ ] Roll back to previous Docker image:
  ```bash
  # Tag previous image as latest
  docker tag $ECR_URL:previous $ECR_URL:latest
  docker push $ECR_URL:latest
  
  # Force deployment
  aws ecs update-service \
    --cluster rivet-dev \
    --service rivet-dev-service \
    --force-new-deployment
  ```

### If Costs Are Too High
- [ ] Scale down immediately:
  ```bash
  # Edit terraform.tfvars: desired_count = 0
  terraform apply
  ```
- [ ] Review and optimize configuration
- [ ] Redeploy with optimizations

## Cleanup Checklist

### When Done Testing
- [ ] Stop ECS tasks to save costs:
  ```bash
  # Edit terraform.tfvars: desired_count = 0
  terraform apply
  ```

### Complete Teardown
- [ ] Backup any important data from S3
- [ ] Export CloudWatch logs if needed
- [ ] Destroy all resources:
  ```bash
  terraform destroy
  ```
- [ ] Verify all resources deleted in AWS Console
- [ ] Check for any orphaned resources
- [ ] Remove local Terraform state if needed

## Success Criteria

Deployment is successful when:
- [ ] All Terraform resources created without errors
- [ ] ECS tasks running and healthy
- [ ] Application accessible via ALB URL
- [ ] Product analysis works end-to-end
- [ ] GenAI tips appear in results
- [ ] CloudWatch logs show no errors
- [ ] Bedrock invocations successful
- [ ] Costs within expected range

## Notes

Use this space to track deployment-specific information:

**Deployment Date**: ___________________________

**Deployed By**: ___________________________

**Application URL**: ___________________________

**ECR Repository**: ___________________________

**Issues Encountered**: 
___________________________
___________________________
___________________________

**Resolutions**: 
___________________________
___________________________
___________________________

**Next Steps**: 
___________________________
___________________________
___________________________
