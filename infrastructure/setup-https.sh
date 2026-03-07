#!/bin/bash
# Setup HTTPS with nginx and Let's Encrypt (FREE)
# Run this on your EC2 instance

set -e

echo "=========================================="
echo "Setting up HTTPS with nginx + Let's Encrypt"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get domain name from user
read -p "Enter your domain name (e.g., rivet.example.com): " DOMAIN
read -p "Enter your email for SSL certificate notifications: " EMAIL

echo ""
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
read -p "Is this correct? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Aborted"
    exit 1
fi

# Install nginx
echo "Installing nginx..."
dnf install -y nginx

# Install certbot for Let's Encrypt
echo "Installing certbot..."
dnf install -y certbot python3-certbot-nginx

# Create nginx configuration
echo "Configuring nginx..."
cat > /etc/nginx/conf.d/rivet.conf <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    # SSL certificates (will be added by certbot)
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to Flask app
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files (if any)
    location /static {
        proxy_pass http://localhost:8000/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Start nginx
echo "Starting nginx..."
systemctl start nginx
systemctl enable nginx

# Open firewall ports
echo "Configuring firewall..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
fi

# Get SSL certificate
echo "Obtaining SSL certificate from Let's Encrypt..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

# Setup auto-renewal
echo "Setting up automatic certificate renewal..."
systemctl enable certbot-renew.timer
systemctl start certbot-renew.timer

echo ""
echo "=========================================="
echo "✓ HTTPS Setup Complete!"
echo "=========================================="
echo ""
echo "Your site is now available at: https://$DOMAIN"
echo ""
echo "Certificate will auto-renew before expiration."
echo "Check renewal status: certbot renew --dry-run"
echo ""
echo "IMPORTANT: Make sure your domain DNS points to this server's IP:"
curl -s http://checkip.amazonaws.com
echo ""
