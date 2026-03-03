# Quick Start: Deployment Upgrade

This guide gets you up and running with the new CI/CD pipeline and Bedrock integration in under 30 minutes.

## Prerequisites

- AWS CLI configured with admin access
- GitHub repository with this code
- Terraform installed (v1.5+)
- Existing infrastructure deployed

## Step 1: Enable Bedrock Model Access (5 minutes)

1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Click "Model access" in left sidebar
3. Click "Manage model access"
4. Enable these models:
   - ✅ Claude 3.5 Sonnet
   - ✅ Claude 3.5 Haiku
   - ✅ Amazon Titan Image Generator v2
5. Click "Save changes"
6. Wait for status to show "Access granted" (usually instant)

## Step 2: Set Up GitHub Actions (10 minutes)

### 2.1 Create OIDC Provider

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2.2 Create IAM Policy

```bash
cd infrastructure
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-iam-policy.json
```

Copy the policy ARN from output (you'll need it next).

### 2.3 Create Trust Policy File

Create `github-actions-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
      }
    }
  }]
}
```

Replace:
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_ORG/YOUR_REPO` with your GitHub repo (e.g., `acme/rivet`)

### 2.4 Create IAM Role

```bash
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://github-actions-trust-policy.json

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeployPolicy
```

### 2.5 Add GitHub Secret

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AWS_ROLE_ARN`
4. Value: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsDeployRole`
5. Click "Add secret"

## Step 3: Update Terraform Configuration (5 minutes)

### 3.1 Create/Update terraform.tfvars

```bash
cd infrastructure/environments/dev
```

Create or edit `terraform.tfvars`:

```hcl
# AWS Configuration
aws_region         = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b"]

# Enable Bedrock (NEW)
use_bedrock = true

# Bedrock Model IDs (UPDATED)
draft_model_id         = "anthropic.claude-3-5-haiku-20241022-v1:0"
critic_model_id        = "anthropic.claude-3-5-sonnet-20241022-v2:0"
vision_model_id        = ""
bedrock_image_model_id = "amazon.titan-image-generator-v2:0"

# Anthropic API Key (optional - only needed if use_bedrock=false)
# anthropic_api_key = "sk-ant-..."

# Instance Configuration
instance_type    = "t3.small"
min_size         = 1
max_size         = 3
desired_capacity = 1
```

### 3.2 Apply Terraform Changes

```bash
terraform init
terraform plan
terraform apply
```

Type `yes` when prompted.

This will:
- Update EC2 launch template with Bedrock configuration
- Trigger instance refresh (takes ~30 minutes)
- Deploy new instances with Bedrock enabled

## Step 4: Verify Deployment (5 minutes)

### 4.1 Check Instance Refresh

```bash
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg \
  --max-records 1
```

Wait for `Status: "Successful"` (takes ~30 minutes).

### 4.2 Check Application Logs

```bash
aws logs tail /ec2/rivet-dev --follow
```

Look for:
```
Bedrock client initialized [region=us-east-1]
Rivet app started [env=development]
```

### 4.3 Test Application

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?Tags[?Key=='Project' && Value=='rivet']].DNSName" \
  --output text)

# Test health endpoint
curl http://$ALB_DNS/

# Should return 200 OK
```

## Step 5: Test CI/CD Pipeline (5 minutes)

### 5.1 Make a Test Commit

```bash
git commit --allow-empty -m "Test CI/CD pipeline"
git push origin main
```

### 5.2 Monitor Deployment

1. Go to GitHub → Actions tab
2. Click on the running workflow
3. Watch the deployment progress

Expected steps:
- ✅ Checkout code
- ✅ Configure AWS credentials
- ✅ Login to ECR
- ✅ Build and push image
- ✅ Trigger instance refresh
- ✅ Wait for deployment
- ✅ Verify deployment

Total time: ~30-40 minutes

## Verification Checklist

After deployment completes, verify:

- [ ] Instance refresh status is "Successful"
- [ ] New EC2 instances are running
- [ ] Application responds to HTTP requests
- [ ] CloudWatch logs show Bedrock initialization
- [ ] GitHub Actions workflow completed successfully
- [ ] No errors in CloudWatch logs

## Quick Commands Reference

```bash
# Check instance refresh status
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg --max-records 1

# Check EC2 instances
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=rivet" \
  --query "Reservations[].Instances[].[InstanceId,State.Name,LaunchTime]" \
  --output table

# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --query "TargetGroups[?Tags[?Key=='Project' && Value=='rivet']].TargetGroupArn" \
    --output text)

# View application logs
aws logs tail /ec2/rivet-dev --follow

# Check Bedrock invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=anthropic.claude-3-5-haiku-20241022-v1:0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## Troubleshooting

### Issue: Terraform apply fails with "Secret not found"

**Solution**: The Anthropic API key is now optional when using Bedrock. Either:
1. Set `use_bedrock = true` in terraform.tfvars (recommended)
2. Or provide `anthropic_api_key` for backward compatibility

### Issue: Instance refresh fails

**Solution**: Check CloudWatch logs for errors:
```bash
aws logs tail /ec2/rivet-dev --follow
```

Common causes:
- Docker image pull failed (check ECR permissions)
- Container failed to start (check environment variables)
- Health check failed (check application logs)

### Issue: GitHub Actions fails at "Login to ECR"

**Solution**: Verify IAM role has ECR permissions:
```bash
aws iam get-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-name GitHubActionsDeployPolicy
```

### Issue: Bedrock AccessDenied error

**Solution**: Verify:
1. Bedrock models are enabled in console
2. IAM role has `bedrock:InvokeModel` permission
3. Region is `us-east-1`

## Next Steps

1. **Monitor Costs**: Set up billing alerts in AWS Cost Explorer
2. **Set Up Dashboards**: Create CloudWatch dashboards for metrics
3. **Configure Alarms**: Set up alerts for errors and high latency
4. **Document Runbooks**: Create team documentation for common tasks
5. **Test Rollback**: Practice rollback procedure in dev environment

## Support

- **Detailed Guides**:
  - CI/CD: `infrastructure/CI_CD_SETUP.md`
  - Bedrock: `infrastructure/BEDROCK_MIGRATION.md`
  - Full Summary: `DEPLOYMENT_UPGRADE_SUMMARY.md`

- **AWS Documentation**:
  - Bedrock: https://docs.aws.amazon.com/bedrock/
  - Auto Scaling: https://docs.aws.amazon.com/autoscaling/

- **GitHub Actions**:
  - Workflow: `.github/workflows/deploy.yml`
  - Docs: https://docs.github.com/actions

## Success Criteria

You've successfully completed the upgrade when:

✅ Terraform apply completes without errors
✅ Instance refresh completes successfully
✅ Application responds to HTTP requests
✅ CloudWatch logs show Bedrock initialization
✅ GitHub Actions workflow deploys successfully
✅ No errors in application logs
✅ Bedrock invocations appear in CloudWatch metrics

Congratulations! Your deployment is now automated and using AWS Bedrock. 🎉
