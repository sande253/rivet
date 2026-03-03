#!/bin/bash
# Rivet Terraform Prerequisites Validation Script
# Run this before terraform init to ensure all requirements are met

set -e

echo "=========================================="
echo "Rivet Terraform Prerequisites Validation"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ((ERRORS++))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Check AWS CLI
echo "Checking AWS CLI..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    print_status 0 "AWS CLI installed (version $AWS_VERSION)"
else
    print_status 1 "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
fi

# Check AWS credentials
echo ""
echo "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    print_status 0 "AWS credentials configured"
    echo "   Account: $AWS_ACCOUNT"
    echo "   Identity: $AWS_USER"
else
    print_status 1 "AWS credentials not configured. Run: aws configure"
fi

# Check AWS region
echo ""
echo "Checking AWS region..."
AWS_REGION=$(aws configure get region 2>/dev/null || echo "")
if [ "$AWS_REGION" = "us-east-1" ]; then
    print_status 0 "AWS region set to us-east-1"
elif [ -n "$AWS_REGION" ]; then
    print_warning "AWS region is $AWS_REGION (Bedrock models may not be available)"
    echo "   Recommended: us-east-1 for full Bedrock model access"
else
    print_status 1 "AWS region not configured. Run: aws configure set region us-east-1"
fi

# Check Terraform
echo ""
echo "Checking Terraform..."
if command -v terraform &> /dev/null; then
    TF_VERSION=$(terraform version -json 2>/dev/null | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
    if [ -z "$TF_VERSION" ]; then
        TF_VERSION=$(terraform version | head -n1 | cut -d'v' -f2)
    fi
    
    # Check if version >= 1.5
    TF_MAJOR=$(echo $TF_VERSION | cut -d'.' -f1)
    TF_MINOR=$(echo $TF_VERSION | cut -d'.' -f2)
    
    if [ "$TF_MAJOR" -ge 1 ] && [ "$TF_MINOR" -ge 5 ]; then
        print_status 0 "Terraform installed (version $TF_VERSION)"
    else
        print_warning "Terraform version $TF_VERSION found, but >= 1.5 required"
    fi
else
    print_status 1 "Terraform not found. Install from: https://www.terraform.io/downloads"
fi

# Check Anthropic API key
echo ""
echo "Checking Anthropic API key..."
if [ -n "$TF_VAR_anthropic_api_key" ]; then
    if [[ "$TF_VAR_anthropic_api_key" == sk-ant-* ]]; then
        print_status 0 "Anthropic API key set (TF_VAR_anthropic_api_key)"
        echo "   Key: ${TF_VAR_anthropic_api_key:0:15}..."
    else
        print_warning "TF_VAR_anthropic_api_key set but doesn't look like a valid key"
        echo "   Expected format: sk-ant-..."
    fi
else
    print_status 1 "Anthropic API key not set"
    echo "   Run: export TF_VAR_anthropic_api_key=\"sk-ant-your-key-here\""
fi

# Check Bedrock model access
echo ""
echo "Checking Bedrock model access..."
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
    REGION=${AWS_REGION:-us-east-1}
    
    # Try to list foundation models
    if aws bedrock list-foundation-models --region $REGION &> /dev/null; then
        CLAUDE_MODELS=$(aws bedrock list-foundation-models --region $REGION \
            --query 'modelSummaries[?contains(modelId, `claude`)].modelId' \
            --output text 2>/dev/null | wc -w)
        
        if [ "$CLAUDE_MODELS" -gt 0 ]; then
            print_status 0 "Bedrock access enabled ($CLAUDE_MODELS Claude models available)"
        else
            print_warning "Bedrock accessible but no Claude models found"
            echo "   Request access: AWS Console → Bedrock → Model access"
        fi
    else
        print_warning "Cannot access Bedrock (may need to enable in region $REGION)"
        echo "   Enable: AWS Console → Bedrock → Model access"
    fi
else
    print_warning "Skipping Bedrock check (AWS CLI or credentials not available)"
fi

# Check S3 state bucket
echo ""
echo "Checking S3 state bucket..."
STATE_BUCKET="tf-rivet-project-bucket"
if aws s3 ls s3://$STATE_BUCKET &> /dev/null; then
    print_status 0 "S3 state bucket exists ($STATE_BUCKET)"
else
    print_warning "S3 state bucket not found ($STATE_BUCKET)"
    echo "   Terraform will create it on first apply"
fi

# Check Docker (optional)
echo ""
echo "Checking Docker (optional)..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    print_status 0 "Docker installed (version $DOCKER_VERSION)"
else
    print_warning "Docker not found (needed to build and push application image)"
    echo "   Install from: https://docs.docker.com/get-docker/"
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to deploy. Run:"
    echo "  terraform init"
    echo "  terraform plan"
    echo "  terraform apply"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
    echo ""
    echo "You can proceed, but review warnings above."
    echo "Run: terraform init"
else
    echo -e "${RED}✗ $ERRORS error(s) found${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
    fi
    echo ""
    echo "Fix errors above before running terraform init"
    exit 1
fi

echo ""
