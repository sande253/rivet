# CI/CD Pipeline Setup Guide

This guide explains how to set up the GitHub Actions CI/CD pipeline for automated deployments to AWS EC2.

## Overview

The CI/CD pipeline automatically:
1. Builds Docker images on every push to `main` or `dev` branches
2. Pushes images to Amazon ECR with commit SHA and `latest` tags
3. Triggers zero-downtime instance refresh in Auto Scaling Group
4. Verifies deployment health

## Prerequisites

- GitHub repository with this codebase
- AWS account with existing infrastructure deployed
- GitHub repository secrets configured

## Step 1: Create IAM Role for GitHub Actions

### 1.1 Create OIDC Identity Provider

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 1.2 Create IAM Policy

```bash
cd infrastructure
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-iam-policy.json
```

Note the policy ARN from the output.

### 1.3 Create IAM Role with Trust Policy

Create a file `github-actions-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

Replace:
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_GITHUB_ORG/YOUR_REPO` with your GitHub repository (e.g., `myorg/rivet`)

Create the role:

```bash
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://github-actions-trust-policy.json

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeployPolicy
```

## Step 2: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secret:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AWS_ROLE_ARN` | `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsDeployRole` | IAM role ARN for GitHub Actions |

## Step 3: Verify Workflow File

The workflow file is already created at `.github/workflows/deploy.yml`. Review it to ensure:

- `AWS_REGION` matches your deployment region (default: `us-east-1`)
- `ECR_REPOSITORY` matches your ECR repository name (default: `rivet-dev`)
- `CONTAINER_NAME` matches your container name (default: `rivet-backend`)

## Step 4: Test the Pipeline

### 4.1 Manual Trigger

1. Go to GitHub → Actions → "Deploy to AWS EC2"
2. Click "Run workflow"
3. Select branch and click "Run workflow"

### 4.2 Automatic Trigger

Push a commit to `main` or `dev` branch:

```bash
git add .
git commit -m "Test CI/CD pipeline"
git push origin main
```

## Step 5: Monitor Deployment

### In GitHub Actions

1. Go to Actions tab in your repository
2. Click on the running workflow
3. Monitor each step's progress

### In AWS Console

1. **ECR**: Verify new image is pushed
   ```bash
   aws ecr describe-images --repository-name rivet-dev --max-items 5
   ```

2. **Auto Scaling Group**: Check instance refresh status
   ```bash
   aws autoscaling describe-instance-refreshes \
     --auto-scaling-group-name rivet-dev-asg
   ```

3. **CloudWatch Logs**: Monitor application logs
   ```bash
   aws logs tail /ec2/rivet-dev --follow
   ```

## Deployment Process

### Zero-Downtime Strategy

The pipeline uses AWS Auto Scaling Group Instance Refresh with:

- **MinHealthyPercentage**: 90% (keeps 90% of instances healthy during refresh)
- **InstanceWarmup**: 300 seconds (5 minutes for new instances to warm up)
- **CheckpointPercentages**: [50, 100] (pauses at 50% and 100% completion)
- **CheckpointDelay**: 300 seconds (waits 5 minutes at each checkpoint)

### Deployment Timeline

1. **Build & Push** (2-5 minutes): Docker image build and ECR push
2. **Instance Refresh Start** (immediate): ASG begins replacing instances
3. **First Instance** (5-10 minutes): New instance launches, pulls image, starts container
4. **Health Check** (2-3 minutes): ALB verifies instance health
5. **Checkpoint 50%** (5 minutes): Pause to verify stability
6. **Remaining Instances** (5-10 minutes): Replace remaining instances
7. **Checkpoint 100%** (5 minutes): Final verification
8. **Total Time**: ~25-40 minutes for complete deployment

### Rollback Strategy

If deployment fails:

1. **Automatic Rollback**: Instance refresh automatically cancels on health check failures
2. **Manual Rollback**: Cancel instance refresh and deploy previous image
   ```bash
   # Cancel current refresh
   aws autoscaling cancel-instance-refresh \
     --auto-scaling-group-name rivet-dev-asg
   
   # Deploy previous image
   git revert HEAD
   git push origin main
   ```

## Troubleshooting

### Pipeline Fails at "Login to Amazon ECR"

**Issue**: IAM role doesn't have ECR permissions

**Solution**: Verify IAM policy includes `ecr:GetAuthorizationToken`

### Pipeline Fails at "Get Auto Scaling Group name"

**Issue**: ASG not found or missing tags

**Solution**: Verify ASG has tags:
- `Project=rivet`
- `Environment=dev`

### Instance Refresh Fails

**Issue**: New instances fail health checks

**Solution**: 
1. Check CloudWatch logs: `aws logs tail /ec2/rivet-dev --follow`
2. Verify Docker container is running on new instances
3. Check ALB target health

### Deployment Timeout

**Issue**: Instance refresh takes longer than 30 minutes

**Solution**: Increase timeout in workflow or check for stuck instances

## Advanced Configuration

### Multi-Environment Deployment

To deploy to different environments (dev, staging, prod):

1. Create separate ECR repositories
2. Create separate IAM roles per environment
3. Add environment-specific secrets in GitHub
4. Modify workflow to use environment variables

### Blue-Green Deployment

For even safer deployments:

1. Create a second Auto Scaling Group
2. Use weighted target groups in ALB
3. Gradually shift traffic from old to new ASG
4. Requires additional Terraform configuration

### Deployment Notifications

Add Slack/Email notifications:

```yaml
- name: Notify deployment status
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Security Best Practices

1. **Never commit AWS credentials** - Use OIDC and IAM roles
2. **Least privilege** - IAM role has minimal required permissions
3. **Audit logs** - CloudTrail logs all API calls
4. **Secrets rotation** - Rotate IAM role credentials regularly
5. **Branch protection** - Require PR reviews before merging to main

## Cost Optimization

- Instance refresh creates temporary duplicate instances (~30 minutes)
- Estimated cost per deployment: $0.10-0.50 (depending on instance type)
- Use smaller instance types for dev environment
- Consider scheduled deployments during off-peak hours

## Next Steps

1. Set up staging environment for pre-production testing
2. Add automated tests before deployment
3. Implement deployment approval gates for production
4. Set up monitoring and alerting for deployment failures
5. Document rollback procedures for your team
