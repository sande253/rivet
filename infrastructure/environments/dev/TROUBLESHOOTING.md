# Terraform Deployment Troubleshooting Guide

## Current Errors and Solutions

### Error 1: Missing Anthropic API Key

**Error Message:**
```
Error: putting Secrets Manager Secret value: You must provide either SecretString or SecretBinary.
```

**Cause:** The `TF_VAR_anthropic_api_key` environment variable is not set.

**Solution:**
```bash
# Set the API key environment variable
export TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"

# Verify it's set
echo $TF_VAR_anthropic_api_key

# Then run terraform apply again
terraform apply
```

**For Windows PowerShell:**
```powershell
$env:TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"
echo $env:TF_VAR_anthropic_api_key
terraform apply
```

---

### Error 2: IAM Permission Denied for ECS

**Error Messages:**
```
AccessDeniedException: User: arn:aws:iam::976792586595:user/rivet_adm is not authorized to perform:
- ecs:CreateCluster
- ecs:RegisterTaskDefinition
```

**Cause:** The IAM user `rivet_adm` lacks ECS permissions.

**Solution:** Attach the following IAM policy to the `rivet_adm` user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

**AWS CLI Command:**
```bash
# Create the policy file
cat > ecs-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
  --policy-name RivetECSFullAccess \
  --policy-document file://ecs-policy.json

aws iam attach-user-policy \
  --user-name rivet_adm \
  --policy-arn arn:aws:iam::976792586595:policy/RivetECSFullAccess
```

---

### Error 3: IAM Permission Denied for SSM

**Error Messages:**
```
AccessDeniedException: User: arn:aws:iam::976792586595:user/rivet_adm is not authorized to perform:
- ssm:PutParameter
```

**Cause:** The IAM user `rivet_adm` lacks SSM Parameter Store permissions.

**Solution:** Attach the following IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:DeleteParameter",
        "ssm:DescribeParameters",
        "ssm:AddTagsToResource",
        "ssm:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

**AWS CLI Command:**
```bash
# Create the policy file
cat > ssm-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:DeleteParameter",
        "ssm:DescribeParameters",
        "ssm:AddTagsToResource",
        "ssm:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
  --policy-name RivetSSMFullAccess \
  --policy-document file://ssm-policy.json

aws iam attach-user-policy \
  --user-name rivet_adm \
  --policy-arn arn:aws:iam::976792586595:policy/RivetSSMFullAccess
```

---

### Error 4: CloudWatch Log Group Does Not Exist

**Error Message:**
```
ResourceNotFoundException: The specified log group does not exist.
```

**Cause:** Metric filters are trying to reference a log group that hasn't been created yet.

**Solution:** This has been fixed in the code by disabling metric filters on first apply. After the initial deployment completes:

1. Edit `infrastructure/environments/dev/main.tf`
2. Change `create_metric_filters = false` to `create_metric_filters = true`
3. Run `terraform apply` again to create the metric filters

---

## Complete IAM Policy for rivet_adm User

For a complete deployment, the `rivet_adm` user needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "ecs:*",
        "ecr:*",
        "elasticloadbalancing:*",
        "s3:*",
        "iam:*",
        "secretsmanager:*",
        "ssm:*",
        "logs:*",
        "cloudwatch:*",
        "bedrock:*",
        "application-autoscaling:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Quick Fix - Attach AWS Managed Policies:**
```bash
# Attach comprehensive managed policies
aws iam attach-user-policy \
  --user-name rivet_adm \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Or for full admin access (not recommended for production)
aws iam attach-user-policy \
  --user-name rivet_adm \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

---

## Step-by-Step Recovery Process

### Step 1: Set API Key
```bash
export TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"
```

### Step 2: Add IAM Permissions

**Option A: Use AWS Console**
1. Go to IAM → Users → rivet_adm
2. Click "Add permissions" → "Attach policies directly"
3. Search and attach:
   - `PowerUserAccess` (or `AdministratorAccess` for full access)

**Option B: Use AWS CLI**
```bash
aws iam attach-user-policy \
  --user-name rivet_adm \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### Step 3: Clean Up Failed Resources (if needed)
```bash
# Check what was created
terraform state list

# If there are partial resources, you can either:
# Option 1: Let terraform retry (recommended)
terraform apply

# Option 2: Destroy and start fresh
terraform destroy
terraform apply
```

### Step 4: Apply Configuration
```bash
terraform apply
```

### Step 5: Enable Metric Filters (After First Apply)
```bash
# Edit main.tf and change:
# create_metric_filters = false
# to:
# create_metric_filters = true

terraform apply
```

---

## Verification Commands

### Check IAM Permissions
```bash
# Check current user
aws sts get-caller-identity

# List attached policies
aws iam list-attached-user-policies --user-name rivet_adm

# Test ECS access
aws ecs list-clusters

# Test SSM access
aws ssm describe-parameters --max-results 10
```

### Check Environment Variables
```bash
# Linux/Mac
echo $TF_VAR_anthropic_api_key

# Windows PowerShell
echo $env:TF_VAR_anthropic_api_key
```

### Check Terraform State
```bash
# List all resources
terraform state list

# Show specific resource
terraform state show module.secrets.aws_secretsmanager_secret.anthropic_api_key
```

---

## Common Issues and Quick Fixes

### Issue: "Secret already exists"
```bash
# Delete the existing secret
aws secretsmanager delete-secret \
  --secret-id rivet-dev/anthropic-api-key \
  --force-delete-without-recovery

# Then retry
terraform apply
```

### Issue: "Parameter already exists"
```bash
# Delete existing parameters
aws ssm delete-parameter --name /rivet-dev/genai/draft-model-id
aws ssm delete-parameter --name /rivet-dev/genai/critic-model-id
aws ssm delete-parameter --name /rivet-dev/genai/vision-model-id
aws ssm delete-parameter --name /rivet-dev/genai/bedrock-image-model-id

# Then retry
terraform apply
```

### Issue: "ECS cluster already exists"
```bash
# Delete the cluster
aws ecs delete-cluster --cluster rivet-dev

# Then retry
terraform apply
```

### Issue: Terraform state is corrupted
```bash
# Backup current state
cp terraform.tfstate terraform.tfstate.backup

# Refresh state from AWS
terraform refresh

# Or start fresh (WARNING: destroys everything)
terraform destroy
rm -rf .terraform terraform.tfstate*
terraform init
terraform apply
```

---

## Prevention for Future Deployments

### 1. Always Set API Key First
```bash
# Add to your shell profile (~/.bashrc or ~/.zshrc)
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
```

### 2. Verify IAM Permissions Before Deployment
```bash
# Run the validation script
./validate.sh

# Or manually check
aws ecs list-clusters
aws ssm describe-parameters
aws secretsmanager list-secrets
```

### 3. Use Terraform Workspaces for Isolation
```bash
# Create a workspace for testing
terraform workspace new test
terraform apply

# Switch back to default
terraform workspace select default
```

### 4. Enable Terraform Logging for Debugging
```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform-debug.log
terraform apply
```

---

## Contact and Support

If issues persist:
1. Check Terraform state: `terraform state list`
2. Review AWS CloudTrail for permission errors
3. Check Terraform debug logs: `TF_LOG=DEBUG terraform apply`
4. Review the main README.md for detailed documentation

## Quick Reference

```bash
# Complete deployment from scratch
export TF_VAR_anthropic_api_key="sk-ant-your-key-here"
terraform init
terraform apply

# After first apply, enable metric filters
# Edit main.tf: create_metric_filters = true
terraform apply

# Verify deployment
terraform output
aws ecs list-clusters
aws ssm get-parameter --name /rivet-dev/genai/draft-model-id
```
