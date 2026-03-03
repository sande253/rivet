# Quick script to set API key and verify it's working

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Set Anthropic API Key" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Please enter your Anthropic API key:" -ForegroundColor Yellow
Write-Host "(Get it from: https://console.anthropic.com/)" -ForegroundColor Gray
Write-Host ""

$apiKey = Read-Host "API Key (starts with sk-ant-)"

if ($apiKey -and $apiKey.StartsWith("sk-ant-")) {
    $env:TF_VAR_anthropic_api_key = $apiKey
    Write-Host ""
    Write-Host "✓ API key set successfully!" -ForegroundColor Green
    Write-Host "  Key: $($apiKey.Substring(0, 15))..." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Verification:" -ForegroundColor Cyan
    Write-Host "  Environment variable: $env:TF_VAR_anthropic_api_key" -ForegroundColor Gray
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Ready to Deploy!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run this command now:" -ForegroundColor Yellow
    Write-Host "  terraform apply" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Invalid API key format" -ForegroundColor Red
    Write-Host "API key must start with 'sk-ant-'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Example: sk-ant-api03-abc123..." -ForegroundColor Gray
    exit 1
}
