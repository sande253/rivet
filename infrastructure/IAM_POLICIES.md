# IAM Policies Reference

This document describes all IAM policies used in the Rivet deployment.

## Overview

The deployment uses three main IAM roles:

1. **EC2 Instance Role** - For application runtime
2. **GitHub Actions Role** - For CI/CD deployments
3. **Terraform Role** - For infrastructure management (optional)

## 1. EC2 Instance Role

### Role Name
`rivet-dev-ec2-role`

### Purpose
Allows EC2 instances to:
- Pull Docker images from ECR
- Invoke Bedrock models
- Read secrets from Secrets Manager
- Write logs to CloudWatch
- Access S3 for uploads

### Attached Policies

#### 1.1 AWS Managed Policies

```hcl
# ECR Read Access
arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# CloudWatch Logs
arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
```

#### 1.2 Custom Policies

**Bedrock Invoke Policy** (`rivet-dev-bedrock-invoke`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-opus-*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-*"
      ]
    },
    {
      "Sid": "BedrockModelList",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/bedrock/rivet-dev:*"
    }
  ]
}
```

**Secrets Manager Read Policy** (`rivet-dev-read-secret`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:rivet-dev-anthropic-*"
    }
  ]
}
```

**SSM Parameter Read Policy** (`rivet-dev-read-ssm`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:us-east-1:*:parameter/rivet/dev/*"
    }
  ]
}
```

**S3 Access Policy** (`rivet-dev-s3-access`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::rivet-dev-uploads",
        "arn:aws:s3:::rivet-dev-uploads/*"
      ]
    }
  ]
}
```

**CloudWatch Metrics Policy** (`rivet-dev-cloudwatch-metrics`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "Rivet/dev"
        }
      }
    }
  ]
}
```

### Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## 2. GitHub Actions Role

### Role Name
`GitHubActionsDeployRole`

### Purpose
Allows GitHub Actions to:
- Push Docker images to ECR
- Trigger Auto Scaling Group instance refresh
- Query ALB and target group status
- Read EC2 instance information

### Policy Document

File: `infrastructure/github-actions-iam-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AutoScalingAccess",
      "Effect": "Allow",
      "Action": [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeInstanceRefreshes",
        "autoscaling:StartInstanceRefresh",
        "autoscaling:CancelInstanceRefresh"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LoadBalancerAccess",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DescribeTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2ReadAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeTags"
      ],
      "Resource": "*"
    }
  ]
}
```

### Trust Policy

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
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

**Important**: Replace `YOUR_ACCOUNT_ID`, `YOUR_ORG`, and `YOUR_REPO` with actual values.

---

## 3. Terraform Role (Optional)

### Role Name
`TerraformDeployRole`

### Purpose
Allows Terraform to manage all infrastructure resources.

### Recommended Policy

For production, use a custom policy with least privilege. For development, you can use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "elasticloadbalancing:*",
        "autoscaling:*",
        "ecr:*",
        "s3:*",
        "secretsmanager:*",
        "ssm:*",
        "iam:*",
        "logs:*",
        "cloudwatch:*",
        "bedrock:*",
        "cloudfront:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Warning**: This is very permissive. For production, restrict to specific resources.

---

## Security Best Practices

### 1. Least Privilege

Each role has only the permissions it needs:

- ✅ EC2 role cannot modify infrastructure
- ✅ GitHub Actions role cannot access application data
- ✅ Bedrock access limited to specific models

### 2. Resource Restrictions

Where possible, policies are restricted to specific resources:

```json
"Resource": "arn:aws:s3:::rivet-dev-uploads/*"
```

Instead of:

```json
"Resource": "*"
```

### 3. Condition Keys

Use conditions to further restrict access:

```json
"Condition": {
  "StringEquals": {
    "cloudwatch:namespace": "Rivet/dev"
  }
}
```

### 4. No Long-Term Credentials

- ✅ EC2 uses instance profile (temporary credentials)
- ✅ GitHub Actions uses OIDC (no stored credentials)
- ✅ Bedrock uses IAM role (no API keys)

### 5. Audit Logging

All IAM actions are logged to CloudTrail:

```bash
# View recent IAM actions
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::IAM::Role \
  --max-results 10
```

---

## Policy Testing

### Test EC2 Role

SSH into an EC2 instance and test:

```bash
# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test S3 access
aws s3 ls s3://rivet-dev-uploads/

# Test Secrets Manager access
aws secretsmanager get-secret-value \
  --secret-id rivet-dev-anthropic-key \
  --region us-east-1
```

### Test GitHub Actions Role

In GitHub Actions workflow:

```yaml
- name: Test IAM permissions
  run: |
    aws sts get-caller-identity
    aws ecr describe-repositories
    aws autoscaling describe-auto-scaling-groups
```

---

## Troubleshooting

### AccessDenied Errors

1. **Check role is attached**:
   ```bash
   aws ec2 describe-instances \
     --instance-ids i-xxxxx \
     --query 'Reservations[0].Instances[0].IamInstanceProfile'
   ```

2. **Check policy is attached to role**:
   ```bash
   aws iam list-attached-role-policies \
     --role-name rivet-dev-ec2-role
   ```

3. **Check policy document**:
   ```bash
   aws iam get-policy-version \
     --policy-arn arn:aws:iam::xxx:policy/rivet-dev-bedrock-invoke \
     --version-id v1
   ```

### Bedrock AccessDenied

Common causes:

1. **Model not enabled**: Go to Bedrock console → Model access
2. **Wrong region**: Bedrock is region-specific (use us-east-1)
3. **Wrong model ID**: Use `anthropic.claude-3-5-*` format
4. **IAM policy missing**: Check `bedrock:InvokeModel` permission

### GitHub Actions AccessDenied

Common causes:

1. **OIDC provider not created**: Check IAM → Identity providers
2. **Trust policy incorrect**: Verify repo name in trust policy
3. **Role ARN wrong**: Check GitHub secret `AWS_ROLE_ARN`
4. **Policy not attached**: Check role has policy attached

---

## Policy Updates

### Adding New Permissions

1. Update Terraform policy definition
2. Run `terraform plan` to review changes
3. Run `terraform apply` to deploy
4. Test new permissions

### Removing Permissions

1. Comment out permission in Terraform
2. Run `terraform plan` to verify removal
3. Test application still works
4. Run `terraform apply` to deploy

### Rotating Credentials

For Anthropic API key (if using):

```bash
# Create new secret version
aws secretsmanager update-secret \
  --secret-id rivet-dev-anthropic-key \
  --secret-string "new-api-key"

# Restart application
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name rivet-dev-asg
```

---

## Compliance

### GDPR / Data Protection

- ✅ No PII in IAM policies
- ✅ CloudTrail logs all access
- ✅ Secrets encrypted at rest
- ✅ Temporary credentials only

### SOC 2 / ISO 27001

- ✅ Least privilege access
- ✅ Audit logging enabled
- ✅ Regular policy reviews
- ✅ No shared credentials

### PCI DSS

- ✅ No credentials in code
- ✅ Encrypted secrets
- ✅ Access logging
- ✅ Regular rotation

---

## References

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Bedrock IAM Permissions](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [EC2 Instance Profiles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)

---

## Support

For IAM-related issues:

1. Check CloudTrail logs for AccessDenied events
2. Use IAM Policy Simulator to test permissions
3. Review this document for correct policy format
4. Contact AWS Support for complex issues
