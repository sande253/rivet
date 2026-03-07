#!/bin/bash
# Setup SSL certificate and HTTPS for rivetai.online

set -e

echo "=========================================="
echo "Setting up HTTPS for rivetai.online"
echo "=========================================="

cd "$(dirname "$0")"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Plan the changes
echo ""
echo "Planning SSL certificate and HTTPS setup..."
terraform plan -target=aws_acm_certificate.rivet_ssl \
               -target=aws_acm_certificate_validation.rivet_ssl \
               -target=aws_lb_listener.https \
               -target=aws_lb_listener.http_redirect

echo ""
echo "=========================================="
echo "IMPORTANT: DNS Validation Required"
echo "=========================================="
echo ""
echo "After applying, you'll need to add validation CNAME records to GoDaddy."
echo "The script will show you exactly what to add."
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Aborted"
    exit 0
fi

# Apply the changes
echo ""
echo "Applying changes..."
terraform apply -target=aws_acm_certificate.rivet_ssl \
                -target=aws_acm_certificate_validation.rivet_ssl \
                -target=aws_lb_listener.https \
                -target=aws_lb_listener.http_redirect \
                -auto-approve

echo ""
echo "=========================================="
echo "✓ SSL Certificate Requested!"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Check the output above for 'ssl_validation_records'"
echo "2. Add those CNAME records to GoDaddy DNS"
echo "3. Wait 5-30 minutes for validation"
echo "4. Your site will be live at https://rivetai.online"
echo ""
echo "To check certificate status:"
echo "  terraform output certificate_status"
echo ""
