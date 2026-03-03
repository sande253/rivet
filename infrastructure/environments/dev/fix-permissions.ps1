# PowerShell script to fix IAM permissions for rivet_adm user
# Run this script to add necessary permissions for Terraform deployment

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Rivet IAM Permissions Fix Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Get current user
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    $currentUser = $identity.Arn.Split('/')[-1]
    $accountId = $identity.Account
    
    Write-Host "Current IAM User: $currentUser" -ForegroundColor Green
    Write-Host "AWS Account ID: $accountId" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "Error: Unable to get AWS identity. Make sure AWS CLI is configured." -ForegroundColor Red
    Write-Host "Run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Check if user is rivet_adm
if ($currentUser -ne "rivet_adm") {
    Write-Host "Warning: Current user is not rivet_adm" -ForegroundColor Yellow
    Write-Host "This script is designed for rivet_adm user" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host "Attaching PowerUserAccess policy to user: $currentUser" -ForegroundColor Cyan
Write-Host ""

# Attach PowerUserAccess policy (simplest solution)
try {
    aws iam attach-user-policy `
        --user-name $currentUser `
        --policy-arn arn:aws:iam::aws:policy/PowerUserAccess 2>&1 | Out-Null
    
    Write-Host "✓ Successfully attached PowerUserAccess policy" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*EntityAlreadyExists*" -or $_.Exception.Message -like "*already attached*") {
        Write-Host "✓ PowerUserAccess policy already attached" -ForegroundColor Green
    } else {
        Write-Host "Error attaching policy: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Alternative: Manually attach the policy in AWS Console:" -ForegroundColor Yellow
        Write-Host "1. Go to IAM → Users → $currentUser" -ForegroundColor Yellow
        Write-Host "2. Click 'Add permissions'" -ForegroundColor Yellow
        Write-Host "3. Select 'Attach policies directly'" -ForegroundColor Yellow
        Write-Host "4. Search for and select 'PowerUserAccess'" -ForegroundColor Yellow
        Write-Host "5. Click 'Add permissions'" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Permissions Update Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# List attached policies
Write-Host "Current attached policies:" -ForegroundColor Cyan
aws iam list-attached-user-policies --user-name $currentUser --output table

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Set your Anthropic API key:" -ForegroundColor White
Write-Host '   $env:TF_VAR_anthropic_api_key="sk-ant-your-key-here"' -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run Terraform:" -ForegroundColor White
Write-Host "   terraform apply" -ForegroundColor Gray
Write-Host ""
