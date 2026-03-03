#!/bin/bash
# Deploy CloudFront distribution for Rivet application

set -e

echo "=================================================="
echo "CloudFront Distribution Deployment"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.tf" ]; then
    echo "Error: main.tf not found. Please run this script from infrastructure/environments/dev/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

echo "Step 1: Terraform Plan"
echo "----------------------"
terraform plan -out=cloudfront.tfplan
echo ""

read -p "Do you want to apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    rm -f cloudfront.tfplan
    exit 0
fi

echo ""
echo "Step 2: Terraform Apply"
echo "----------------------"
terraform apply cloudfront.tfplan
rm -f cloudfront.tfplan
echo ""

echo "Step 3: Getting CloudFront URL"
echo "------------------------------"
CLOUDFRONT_URL=$(terraform output -raw cloudfront_url)
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_domain)
echo ""
echo "✅ CloudFront distribution created!"
echo ""
echo "Your new application URL:"
echo "  $CLOUDFRONT_URL"
echo ""
echo "CloudFront domain:"
echo "  $CLOUDFRONT_DOMAIN"
echo ""

echo "Step 4: Checking Distribution Status"
echo "------------------------------------"
echo "CloudFront distributions take 15-20 minutes to deploy globally."
echo ""

# Extract distribution ID from domain
DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='$CLOUDFRONT_DOMAIN'].Id" --output text)

if [ -n "$DIST_ID" ]; then
    echo "Distribution ID: $DIST_ID"
    STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text)
    echo "Current Status: $STATUS"
    echo ""
    
    if [ "$STATUS" = "InProgress" ]; then
        echo "⏳ Distribution is deploying..."
        echo ""
        echo "You can check status with:"
        echo "  aws cloudfront get-distribution --id $DIST_ID --query 'Distribution.Status'"
        echo ""
        echo "Or wait for deployment:"
        echo "  aws cloudfront wait distribution-deployed --id $DIST_ID"
    else
        echo "✅ Distribution is deployed and ready!"
        echo ""
        echo "Test your application:"
        echo "  curl -I $CLOUDFRONT_URL"
        echo ""
        echo "Or open in browser:"
        echo "  start $CLOUDFRONT_URL"
    fi
else
    echo "⚠️  Could not find distribution ID"
    echo "The distribution was created but may take a few minutes to appear in AWS."
fi

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "1. Wait 15-20 minutes for CloudFront to deploy globally"
echo "2. Test the URL: $CLOUDFRONT_URL"
echo "3. Test on your mobile phone"
echo "4. Share the shorter HTTPS URL with users"
echo ""
echo "For more information, see:"
echo "  infrastructure/CLOUDFRONT_SETUP.md"
echo ""
