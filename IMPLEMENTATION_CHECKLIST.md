# Implementation Checklist

Use this checklist to track your progress implementing the deployment upgrades.

## Phase 1: Pre-Deployment Preparation

### AWS Account Setup
- [ ] AWS CLI installed and configured
- [ ] AWS account has admin access
- [ ] Terraform >= 1.5 installed
- [ ] Docker installed (for local testing)

### Bedrock Setup
- [ ] Navigate to AWS Bedrock Console
- [ ] Click "Model access" in sidebar
- [ ] Enable Claude 3.5 Sonnet
- [ ] Enable Claude 3.5 Haiku
- [ ] Enable Amazon Titan Image Generator v2
- [ ] Verify all models show "Access granted"

### GitHub Repository Setup
- [ ] Code pushed to GitHub repository
- [ ] Repository settings accessible
- [ ] Admin access to repository

---

## Phase 2: CI/CD Pipeline Setup

### OIDC Provider Creation
- [ ] Run command to create OIDC provider:
  ```bash
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
  ```
- [ ] Verify provider created in IAM console

### IAM Policy Creation
- [ ] Navigate to `infrastructure/` directory
- [ ] Run command to create policy:
  ```bash
  aws iam create-policy \
    --policy-name GitHubActionsDeployPolicy \
    --policy-document file://github-actions-iam-policy.json
  ```
- [ ] Copy policy ARN from output
- [ ] Save policy ARN for next step

### Trust Policy Configuration
- [ ] Get AWS account ID: `aws sts get-caller-identity --query Account --output text`
- [ ] Get GitHub org/repo name (e.g., `myorg/rivet`)
- [ ] Create `github-actions-trust-policy.json` with correct values
- [ ] Replace `YOUR_ACCOUNT_ID` with actual account ID
- [ ] Replace `YOUR_ORG/YOUR_REPO` with actual repo path

### IAM Role Creation
- [ ] Run command to create role:
  ```bash
  aws iam create-role \
    --role-name GitHubActionsDeployRole \
    --assume-role-policy-document file://github-actions-trust-policy.json
  ```
- [ ] Run command to attach policy:
  ```bash
  aws iam attach-role-policy \
    --role-name GitHubActionsDeployRole \
    --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsDeployPolicy
  ```
- [ ] Verify role created in IAM console

### GitHub Secrets Configuration
- [ ] Go to GitHub repo → Settings → Secrets and variables → Actions
- [ ] Click "New repository secret"
- [ ] Name: `AWS_ROLE_ARN`
- [ ] Value: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActionsDeployRole`
- [ ] Click "Add secret"
- [ ] Verify secret appears in list

### Workflow File Verification
- [ ] Verify `.github/workflows/deploy.yml` exists
- [ ] Check `AWS_REGION` matches your region (default: us-east-1)
- [ ] Check `ECR_REPOSITORY` matches your repo name (default: rivet-dev)
- [ ] Check `CONTAINER_NAME` matches your container (default: rivet-backend)

---

## Phase 3: Terraform Configuration

### Terraform Files Review
- [ ] Navigate to `infrastructure/environments/dev/`
- [ ] Verify `terraform.tfvars.example` exists
- [ ] Copy to `terraform.tfvars`: `cp terraform.tfvars.example terraform.tfvars`

### Variable Configuration
- [ ] Edit `terraform.tfvars`
- [ ] Set `aws_region` (e.g., "us-east-1")
- [ ] Set `availability_zones` (e.g., ["us-east-1a", "us-east-1b"])
- [ ] Set `use_bedrock = true`
- [ ] Set `draft_model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"`
- [ ] Set `critic_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"`
- [ ] Set `bedrock_image_model_id = "amazon.titan-image-generator-v2:0"`
- [ ] Set `instance_type` (e.g., "t3.small")
- [ ] Set `min_size`, `max_size`, `desired_capacity`
- [ ] Review all other variables

### Terraform Backend Configuration
- [ ] Verify S3 bucket for Terraform state exists
- [ ] Update `backend "s3"` block in `main.tf` if needed
- [ ] Ensure bucket name is unique

---

## Phase 4: Infrastructure Deployment

### Terraform Initialization
- [ ] Run `terraform init`
- [ ] Verify initialization successful
- [ ] Check backend configured correctly

### Terraform Planning
- [ ] Run `terraform plan`
- [ ] Review all resources to be created/modified
- [ ] Verify no unexpected changes
- [ ] Check for any errors or warnings

### Terraform Apply
- [ ] Run `terraform apply`
- [ ] Review plan one more time
- [ ] Type `yes` to confirm
- [ ] Wait for completion (~10-15 minutes)
- [ ] Note any errors

### Post-Apply Verification
- [ ] Run `terraform output` to see outputs
- [ ] Copy ALB DNS name
- [ ] Copy ECR repository URL
- [ ] Copy CloudFront domain name

---

## Phase 5: Application Deployment

### Docker Image Build
- [ ] Navigate to `application/` directory
- [ ] Build Docker image locally (optional test)
- [ ] Verify Dockerfile exists and is correct

### Initial Image Push
- [ ] Get ECR repository URL from Terraform output
- [ ] Login to ECR:
  ```bash
  aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin <ECR_URL>
  ```
- [ ] Build image: `docker build -t <ECR_URL>:latest .`
- [ ] Push image: `docker push <ECR_URL>:latest`
- [ ] Verify image in ECR console

### Instance Refresh Wait
- [ ] Wait for Auto Scaling Group instance refresh (~30 minutes)
- [ ] Monitor progress:
  ```bash
  aws autoscaling describe-instance-refreshes \
    --auto-scaling-group-name rivet-dev-asg --max-records 1
  ```
- [ ] Wait for `Status: "Successful"`

---

## Phase 6: Verification

### Infrastructure Verification
- [ ] Check EC2 instances are running:
  ```bash
  aws ec2 describe-instances \
    --filters "Name=tag:Project,Values=rivet" \
    --query "Reservations[].Instances[].[InstanceId,State.Name]"
  ```
- [ ] Check Auto Scaling Group:
  ```bash
  aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names rivet-dev-asg
  ```
- [ ] Check target health:
  ```bash
  aws elbv2 describe-target-health --target-group-arn <TG_ARN>
  ```

### Application Verification
- [ ] Test ALB endpoint: `curl http://<ALB_DNS>/`
- [ ] Verify 200 OK response
- [ ] Test CloudFront endpoint: `curl https://<CF_DOMAIN>/`
- [ ] Verify application loads in browser

### Logs Verification
- [ ] Check CloudWatch logs:
  ```bash
  aws logs tail /ec2/rivet-dev --follow
  ```
- [ ] Look for "Bedrock client initialized"
- [ ] Look for "Rivet app started"
- [ ] Verify no errors in logs

### Bedrock Verification
- [ ] Check Bedrock invocations in CloudWatch:
  ```bash
  aws cloudwatch get-metric-statistics \
    --namespace AWS/Bedrock \
    --metric-name Invocations \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 3600 \
    --statistics Sum
  ```
- [ ] Test analysis endpoint with sample image
- [ ] Verify Bedrock models are being called

---

## Phase 7: CI/CD Testing

### Manual Workflow Trigger
- [ ] Go to GitHub → Actions tab
- [ ] Click "Deploy to AWS EC2" workflow
- [ ] Click "Run workflow"
- [ ] Select branch (main or dev)
- [ ] Click "Run workflow" button
- [ ] Monitor workflow execution

### Workflow Steps Verification
- [ ] Verify "Checkout code" step passes
- [ ] Verify "Configure AWS credentials" step passes
- [ ] Verify "Login to Amazon ECR" step passes
- [ ] Verify "Build, tag, and push image" step passes
- [ ] Verify "Get Auto Scaling Group name" step passes
- [ ] Verify "Trigger instance refresh" step passes
- [ ] Verify "Wait for deployment" step passes
- [ ] Verify "Verify deployment" step passes

### Automatic Trigger Test
- [ ] Make a test commit:
  ```bash
  git commit --allow-empty -m "Test CI/CD pipeline"
  git push origin main
  ```
- [ ] Verify workflow triggers automatically
- [ ] Monitor deployment progress
- [ ] Wait for completion (~30-40 minutes)

### Post-Deployment Verification
- [ ] Check new image in ECR with commit SHA tag
- [ ] Verify new instances are running
- [ ] Test application endpoint
- [ ] Check CloudWatch logs for new deployment

---

## Phase 8: Monitoring Setup

### CloudWatch Dashboards
- [ ] Create dashboard for deployment metrics
- [ ] Add widget for instance refresh status
- [ ] Add widget for health check failures
- [ ] Add widget for deployment duration

### CloudWatch Alarms
- [ ] Create alarm for high Bedrock latency (>5 seconds)
- [ ] Create alarm for high error rate (>5%)
- [ ] Create alarm for instance refresh failures
- [ ] Create alarm for health check failures
- [ ] Configure SNS topic for alarm notifications

### Cost Monitoring
- [ ] Set up AWS Cost Explorer
- [ ] Create budget for monthly costs
- [ ] Set up budget alerts
- [ ] Configure cost anomaly detection

---

## Phase 9: Documentation

### Team Documentation
- [ ] Share QUICKSTART_DEPLOYMENT.md with team
- [ ] Document custom configuration decisions
- [ ] Create runbook for common operations
- [ ] Document rollback procedures

### Access Documentation
- [ ] Document AWS account access
- [ ] Document GitHub repository access
- [ ] Document who has admin access
- [ ] Document on-call procedures

---

## Phase 10: Post-Deployment

### Security Review
- [ ] Review IAM policies for least privilege
- [ ] Verify no hardcoded credentials in code
- [ ] Check security group rules
- [ ] Review CloudTrail logs

### Performance Baseline
- [ ] Record baseline metrics (CPU, memory, latency)
- [ ] Document typical request patterns
- [ ] Note peak usage times
- [ ] Establish SLAs

### Cost Baseline
- [ ] Record first week costs
- [ ] Compare to estimates
- [ ] Identify optimization opportunities
- [ ] Set up cost tracking

### Team Training
- [ ] Train team on CI/CD pipeline
- [ ] Train team on monitoring dashboards
- [ ] Train team on rollback procedures
- [ ] Train team on troubleshooting

---

## Troubleshooting Checklist

If something goes wrong, check:

### Terraform Issues
- [ ] AWS credentials configured correctly
- [ ] Terraform version >= 1.5
- [ ] S3 backend accessible
- [ ] No conflicting resources

### CI/CD Issues
- [ ] GitHub secret `AWS_ROLE_ARN` set correctly
- [ ] IAM role has correct permissions
- [ ] OIDC provider created
- [ ] Trust policy has correct repo name

### Deployment Issues
- [ ] ECR image exists and is accessible
- [ ] Instance refresh not stuck
- [ ] Health checks passing
- [ ] Security groups allow traffic

### Application Issues
- [ ] Environment variables set correctly
- [ ] Bedrock models enabled
- [ ] IAM role has Bedrock permissions
- [ ] CloudWatch logs show errors

---

## Success Criteria

You've successfully completed the implementation when:

✅ All checklist items above are completed
✅ Terraform apply completes without errors
✅ Instance refresh completes successfully
✅ Application responds to HTTP requests
✅ CloudWatch logs show Bedrock initialization
✅ GitHub Actions workflow deploys successfully
✅ No errors in application logs
✅ Bedrock invocations appear in CloudWatch metrics
✅ Team is trained and documentation is complete

---

## Next Steps

After successful implementation:

1. **Week 1**: Monitor closely, fix any issues
2. **Week 2**: Optimize based on metrics
3. **Month 1**: Review costs and performance
4. **Quarter 1**: Plan for production deployment

---

## Support Resources

- **Quick Start**: QUICKSTART_DEPLOYMENT.md
- **CI/CD Guide**: infrastructure/CI_CD_SETUP.md
- **Bedrock Guide**: infrastructure/BEDROCK_MIGRATION.md
- **IAM Policies**: infrastructure/IAM_POLICIES.md
- **Full Summary**: DEPLOYMENT_UPGRADE_SUMMARY.md

---

## Notes

Use this space to track issues, decisions, or custom configurations:

```
Date: ___________
Issue: ___________________________________________________________
Resolution: ______________________________________________________

Date: ___________
Issue: ___________________________________________________________
Resolution: ______________________________________________________

Date: ___________
Issue: ___________________________________________________________
Resolution: ______________________________________________________
```
