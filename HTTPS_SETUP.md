# FREE HTTPS Setup for Rivet

This guide shows you how to enable HTTPS for FREE using nginx and Let's Encrypt.

## Prerequisites

1. **A domain name** (e.g., rivet.yourdomain.com)
   - You can buy one from Namecheap, GoDaddy, etc. (~$10-15/year)
   - Or use a free subdomain from services like FreeDNS

2. **Domain DNS pointing to your EC2 instance**
   - Get your EC2 public IP from AWS Console
   - Add an A record in your domain DNS settings pointing to that IP

## Setup Steps

### 1. Connect to your EC2 instance

```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

### 2. Download the setup script

```bash
curl -O https://raw.githubusercontent.com/sande253/rivet/main/infrastructure/setup-https.sh
chmod +x setup-https.sh
```

Or copy the script from `infrastructure/setup-https.sh` in this repo.

### 3. Run the setup script

```bash
sudo ./setup-https.sh
```

The script will:
- Install nginx (FREE)
- Install certbot (FREE)
- Configure nginx as reverse proxy
- Get SSL certificate from Let's Encrypt (FREE)
- Set up automatic certificate renewal (FREE)
- Configure HTTP to HTTPS redirect

### 4. Update AWS Security Group

Make sure your EC2 security group allows:
- Port 80 (HTTP) - for Let's Encrypt verification
- Port 443 (HTTPS) - for secure traffic

In AWS Console:
1. Go to EC2 → Security Groups
2. Find your instance's security group
3. Add inbound rules:
   - Type: HTTP, Port: 80, Source: 0.0.0.0/0
   - Type: HTTPS, Port: 443, Source: 0.0.0.0/0

## What You Get (All FREE!)

✅ HTTPS encryption with valid SSL certificate  
✅ Automatic HTTP to HTTPS redirect  
✅ Auto-renewal of SSL certificate (every 90 days)  
✅ Security headers configured  
✅ nginx reverse proxy for better performance  

## Cost Breakdown

- **nginx**: FREE (open source)
- **Let's Encrypt SSL**: FREE (forever)
- **certbot**: FREE (open source)
- **Setup**: FREE (automated script)

**Total additional cost: $0/month** 🎉

You only pay for:
- Domain name: ~$10-15/year (one-time)
- Your existing EC2 instance (already paying for this)

## Troubleshooting

### Certificate not working?

Check if your domain DNS is properly configured:
```bash
nslookup your-domain.com
```

### nginx not starting?

Check logs:
```bash
sudo journalctl -u nginx -n 50
```

### Certificate renewal failing?

Test renewal:
```bash
sudo certbot renew --dry-run
```

## Alternative: Free Domain Options

If you don't want to buy a domain, you can use:

1. **FreeDNS** (freedns.afraid.org) - Free subdomains
2. **DuckDNS** (duckdns.org) - Free dynamic DNS
3. **No-IP** (noip.com) - Free hostname

These work with Let's Encrypt!

## Need Help?

The setup script is fully automated. Just run it and follow the prompts!
