#!/bin/bash
# Quick fix script for IAM permissions

set -e

echo "=========================================="
echo "Rivet IAM Permissions Fix Script"
echo "=========================================="
echo ""

# Get current user
CURRENT_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Current IAM User: $CURRENT_USER"
echo "AWS Account ID: $ACCOUNT_ID"
echo ""

# Check if user is rivet_adm
if [ "$CURRENT_USER" != "rivet_adm" ]; then
    echo "Warning: Current user is not rivet_adm"
    echo "This script is designed for rivet_adm user"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Creating IAM policies for Terraform deployment..."
echo ""

# Create ECS policy
echo "1. Creating ECS policy..."
cat > /tmp/rivet-ecs-policy.json << 'EOF'
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
        "logs:DescribeLogStreams",
        "logs:PutMetricFilter",
        "logs:DeleteMetricFilter",
        "logs:DescribeMetricFilters"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create SSM policy
echo "2. Creating SSM policy..."
cat > /tmp/rivet-ssm-policy.json << 'EOF'
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

# Create Bedrock policy
echo "3. Creating Bedrock policy..."
cat > /tmp/rivet-bedrock-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach policies
echo ""
echo "Attaching policies to user: $CURRENT_USER"
echo ""

# ECS Policy
if aws iam get-policy --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetECSFullAccess 2>/dev/null; then
    echo "✓ RivetECSFullAccess policy already exists"
else
    aws iam create-policy \
      --policy-name RivetECSFullAccess \
      --policy-document file:///tmp/rivet-ecs-policy.json \
      --description "Full access to ECS, ECR, and CloudWatch Logs for Rivet"
    echo "✓ Created RivetECSFullAccess policy"
fi

aws iam attach-user-policy \
  --user-name $CURRENT_USER \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetECSFullAccess 2>/dev/null || echo "  (already attached)"

# SSM Policy
if aws iam get-policy --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetSSMFullAccess 2>/dev/null; then
    echo "✓ RivetSSMFullAccess policy already exists"
else
    aws iam create-policy \
      --policy-name RivetSSMFullAccess \
      --policy-document file:///tmp/rivet-ssm-policy.json \
      --description "Full access to SSM Parameter Store for Rivet"
    echo "✓ Created RivetSSMFullAccess policy"
fi

aws iam attach-user-policy \
  --user-name $CURRENT_USER \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetSSMFullAccess 2>/dev/null || echo "  (already attached)"

# Bedrock Policy
if aws iam get-policy --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetBedrockFullAccess 2>/dev/null; then
    echo "✓ RivetBedrockFullAccess policy already exists"
else
    aws iam create-policy \
      --policy-name RivetBedrockFullAccess \
      --policy-document file:///tmp/rivet-bedrock-policy.json \
      --description "Full access to Bedrock for Rivet"
    echo "✓ Created RivetBedrockFullAccess policy"
fi

aws iam attach-user-policy \
  --user-name $CURRENT_USER \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/RivetBedrockFullAccess 2>/dev/null || echo "  (already attached)"

# Clean up temp files
rm -f /tmp/rivet-ecs-policy.json /tmp/rivet-ssm-policy.json /tmp/rivet-bedrock-policy.json

echo ""
echo "=========================================="
echo "Permissions Update Complete!"
echo "=========================================="
echo ""
echo "Attached policies:"
aws iam list-attached-user-policies --user-name $CURRENT_USER --output table

echo ""
echo "You can now run: terraform apply"
echo ""
