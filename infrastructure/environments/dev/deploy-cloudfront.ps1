# Deploy CloudFront distribution for Rivet application
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "CloudFront Distribution Deployment" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "main.tf")) {
    Write-Host "Error: main.tf not found. Please run this script from infrastructure/environments/dev/" -ForegroundColor Red
    exit 1
}

# Check if AWS credentials are configured
try {
    aws sts get-caller-identity | Out-Null
} catch {
    Write-Host "Error: AWS credentials not configured" -ForegroundColor Red
    Write-Host "Please run: aws configure" -ForegroundColor Yellow
    exit 1
}

Write-Host "Step 1: Terraform Plan" -ForegroundColor Green
Write-Host "----------------------"
terraform plan -out=cloudfront.tfplan
Write-Host ""

$confirm = Read-Host "Do you want to apply these changes? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Deployment cancelled" -ForegroundColor Yellow
    if (Test-Path "cloudfront.tfplan") {
        Remove-Item "cloudfront.tfplan"
    }
    exit 0
}

Write-Host ""
Write-Host "Step 2: Terraform Apply" -ForegroundColor Green
Write-Host "----------------------"
terraform apply cloudfront.tfplan
if (Test-Path "cloudfront.tfplan") {
    Remove-Item "cloudfront.tfplan"
}
Write-Host ""

Write-Host "Step 3: Getting CloudFront URL" -ForegroundColor Green
Write-Host "------------------------------"
$CLOUDFRONT_URL = terraform output -raw cloudfront_url
$CLOUDFRONT_DOMAIN = terraform output -raw cloudfront_domain
Write-Host ""
Write-Host "✅ CloudFront distribution created!" -ForegroundColor Green
Write-Host ""
Write-Host "Your new application URL:" -ForegroundColor Cyan
Write-Host "  $CLOUDFRONT_URL" -ForegroundColor White
Write-Host ""
Write-Host "CloudFront domain:" -ForegroundColor Cyan
Write-Host "  $CLOUDFRONT_DOMAIN" -ForegroundColor White
Write-Host ""

Write-Host "Step 4: Checking Distribution Status" -ForegroundColor Green
Write-Host "------------------------------------"
Write-Host "CloudFront distributions take 15-20 minutes to deploy globally." -ForegroundColor Yellow
Write-Host ""

# Extract distribution ID from domain
$DIST_ID = aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='$CLOUDFRONT_DOMAIN'].Id" --output text

if ($DIST_ID) {
    Write-Host "Distribution ID: $DIST_ID" -ForegroundColor Cyan
    $STATUS = aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text
    Write-Host "Current Status: $STATUS" -ForegroundColor Cyan
    Write-Host ""
    
    if ($STATUS -eq "InProgress") {
        Write-Host "⏳ Distribution is deploying..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "You can check status with:" -ForegroundColor Cyan
        Write-Host "  aws cloudfront get-distribution --id $DIST_ID --query 'Distribution.Status'" -ForegroundColor White
        Write-Host ""
        Write-Host "Or wait for deployment:" -ForegroundColor Cyan
        Write-Host "  aws cloudfront wait distribution-deployed --id $DIST_ID" -ForegroundColor White
    } else {
        Write-Host "✅ Distribution is deployed and ready!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test your application:" -ForegroundColor Cyan
        Write-Host "  curl.exe -I $CLOUDFRONT_URL" -ForegroundColor White
        Write-Host ""
        Write-Host "Or open in browser:" -ForegroundColor Cyan
        Write-Host "  Start-Process '$CLOUDFRONT_URL'" -ForegroundColor White
    }
} else {
    Write-Host "⚠️  Could not find distribution ID" -ForegroundColor Yellow
    Write-Host "The distribution was created but may take a few minutes to appear in AWS."
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "1. Wait 15-20 minutes for CloudFront to deploy globally"
Write-Host "2. Test the URL: $CLOUDFRONT_URL"
Write-Host "3. Test on your mobile phone"
Write-Host "4. Share the shorter HTTPS URL with users"
Write-Host ""
Write-Host "For more information, see:" -ForegroundColor Cyan
Write-Host "  infrastructure/CLOUDFRONT_SETUP.md" -ForegroundColor White
Write-Host ""
