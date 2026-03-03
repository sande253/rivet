# Rivet Deployment Helper Script
# This script guides you through the deployment process

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Rivet Terraform Deployment Helper" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if API key is set
if (-not $env:TF_VAR_anthropic_api_key) {
    Write-Host "❌ Anthropic API key is not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please enter your Anthropic API key:" -ForegroundColor Yellow
    Write-Host "(Get it from: https://console.anthropic.com/)" -ForegroundColor Gray
    Write-Host ""
    $apiKey = Read-Host "API Key (starts with sk-ant-)"
    
    if ($apiKey -and $apiKey.StartsWith("sk-ant-")) {
        $env:TF_VAR_anthropic_api_key = $apiKey
        Write-Host "✓ API key set successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Invalid API key format. Must start with 'sk-ant-'" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ API key is already set" -ForegroundColor Green
    Write-Host "  Key: $($env:TF_VAR_anthropic_api_key.Substring(0, 15))..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting Terraform Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Run terraform apply
terraform apply

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✓ Deployment Successful!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your application URL:" -ForegroundColor Cyan
    terraform output app_url
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Build and push Docker image to ECR" -ForegroundColor White
    Write-Host "2. Deploy application to ECS" -ForegroundColor White
    Write-Host ""
    Write-Host "See README.md for detailed instructions" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "❌ Deployment Failed" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above" -ForegroundColor Yellow
    Write-Host "See TROUBLESHOOTING.md for help" -ForegroundColor Yellow
}
