# Custom URL Solution - CloudFront Distribution

## Problem Summary

You're experiencing DNS resolution issues on your mobile phone:
- ✅ IP address works: `http://34.195.27.39`
- ❌ ALB DNS fails: `http://rivet-dev-alb-734627388.us-east-1.elb.amazonaws.com`
- ❓ Want custom name without buying a domain

## Solution: CloudFront Distribution

I've configured a CloudFront distribution that will give you:
- ✅ Shorter AWS URL (e.g., `d1234abcd.cloudfront.net`)
- ✅ Free HTTPS encryption
- ✅ Better DNS resolution on mobile networks
- ✅ No domain purchase required
- ✅ Global edge caching for better performance

## Quick Start

### Option 1: PowerShell Script (Recommended for Windows)

```powershell
cd infrastructure/environments/dev
.\deploy-cloudfront.ps1
```

### Option 2: Manual Deployment

```powershell
cd infrastructure/environments/dev
terraform plan
terraform apply
```

Wait 15-20 minutes for CloudFront to deploy, then:

```powershell
terraform output cloudfront_url
```

## What Happens

1. **Terraform creates CloudFront distribution** (~2 minutes)
   - Points to your existing ALB
   - Configures HTTPS with free AWS certificate
   - Sets up cache behaviors

2. **CloudFront deploys globally** (~15-20 minutes)
   - Propagates to edge locations worldwide
   - Activates SSL certificate
   - Configures DNS

3. **You get a new URL** (example)
   ```
   https://d1234abcd.cloudfront.net
   ```

4. **Test on mobile**
   - Open the CloudFront URL on your phone
   - Should work on cellular networks
   - Uses HTTPS (secure connection)

## Architecture

```
Your Phone (Mobile Network)
    │
    │ HTTPS (secure)
    ▼
CloudFront Distribution
d1234abcd.cloudfront.net
    │
    │ HTTP
    ▼
Application Load Balancer
rivet-dev-alb-734627388...
    │
    ▼
EC2 Auto Scaling Group
Docker + Flask App
```

## Benefits

### 1. Shorter URL
- **Before**: `http://rivet-dev-alb-734627388.us-east-1.elb.amazonaws.com` (58 chars)
- **After**: `https://d1234abcd.cloudfront.net` (33 chars)

### 2. HTTPS Support
- Free SSL certificate from AWS
- Secure password transmission
- Better for production use

### 3. Better DNS Resolution
- CloudFront uses AWS's global DNS infrastructure
- Better propagation to mobile carriers
- More reliable on cellular networks

### 4. No Cost for Low Traffic
- CloudFront free tier: 1TB data transfer/month
- 10,000,000 requests/month
- Perfect for development

## Files Changed

1. **infrastructure/environments/dev/main.tf**
   - Added CloudFront distribution resource
   - Configured origin pointing to ALB
   - Set up cache behaviors

2. **infrastructure/environments/dev/output.tf**
   - Added `cloudfront_url` output
   - Added `cloudfront_domain` output
   - Updated `app_url` to use CloudFront

3. **New Documentation**
   - `infrastructure/CLOUDFRONT_SETUP.md` - Detailed setup guide
   - `infrastructure/CUSTOM_URL_SOLUTION.md` - This file
   - `infrastructure/environments/dev/deploy-cloudfront.ps1` - Deployment script
   - `infrastructure/environments/dev/deploy-cloudfront.sh` - Bash version

## Deployment Steps

### Step 1: Review Changes

```powershell
cd infrastructure/environments/dev
terraform plan
```

You should see:
- `+ aws_cloudfront_distribution.main` (1 to add)
- `~ output "app_url"` (1 to change)
- `+ output "cloudfront_domain"` (1 to add)
- `+ output "cloudfront_url"` (1 to add)

### Step 2: Apply Changes

```powershell
terraform apply
```

Type `yes` when prompted.

### Step 3: Wait for Deployment

CloudFront takes 15-20 minutes to deploy globally. You can check status:

```powershell
# Get distribution ID
$DOMAIN = terraform output -raw cloudfront_domain
$DIST_ID = aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='$DOMAIN'].Id" --output text

# Check status
aws cloudfront get-distribution --id $DIST_ID --query "Distribution.Status"
```

Status will change from `InProgress` → `Deployed`

### Step 4: Get Your URL

```powershell
terraform output cloudfront_url
```

Example output:
```
https://d1234abcd.cloudfront.net
```

### Step 5: Test

```powershell
# Test from command line
curl.exe -I https://d1234abcd.cloudfront.net

# Or open in browser
Start-Process "https://d1234abcd.cloudfront.net"
```

### Step 6: Test on Mobile

Open the CloudFront URL on your mobile phone. It should:
- ✅ Load successfully
- ✅ Use HTTPS (secure connection)
- ✅ Work on mobile networks
- ✅ Show login page

## Troubleshooting

### "Distribution is still deploying"
**Solution**: Wait 15-20 minutes. CloudFront deploys to edge locations globally.

### "502 Bad Gateway"
**Solution**: 
1. Verify ALB is healthy: `terraform output app_url_alb`
2. Check EC2 instances are running
3. Wait a few more minutes for propagation

### "Login doesn't work"
**Solution**: 
- CloudFront forwards all cookies (required for Flask sessions)
- If issues persist, check Flask session configuration
- Verify `SESSION_COOKIE_SECURE = False` in config.py

### "Still can't access on mobile"
**Solution**:
1. Wait full 20 minutes for global deployment
2. Try clearing mobile browser cache
3. Try different mobile browser
4. Check if mobile network blocks CloudFront (rare)

## Cost

### Free Tier (First 12 Months)
- 1 TB data transfer out
- 10,000,000 HTTP/HTTPS requests
- More than enough for development

### After Free Tier
- ~$8.50/month for 100GB transfer + 1M requests
- Still very affordable for small applications

## Alternative Options

If CloudFront doesn't work for you, here are alternatives:

### Option A: Continue Using IP Address
- **Pros**: Works now, no changes needed
- **Cons**: IP can change if ALB is recreated
- **Cost**: Free

### Option B: Free Subdomain Service
Services like DuckDNS, FreeDNS, or No-IP:
- **Pros**: Custom subdomain (e.g., `rivet.duckdns.org`)
- **Cons**: Requires manual DNS setup, less reliable
- **Cost**: Free

### Option C: Buy Cheap Domain
Domains from Namecheap, GoDaddy, etc:
- **Pros**: Full control, professional appearance
- **Cons**: Costs $10-15/year
- **Cost**: ~$1/month

## Next Steps

1. **Deploy CloudFront** (recommended)
   ```powershell
   cd infrastructure/environments/dev
   .\deploy-cloudfront.ps1
   ```

2. **Wait 15-20 minutes** for global deployment

3. **Test on mobile** with the new HTTPS URL

4. **Share the URL** with users (shorter and more secure)

## Support

If you encounter issues:
1. Check `infrastructure/CLOUDFRONT_SETUP.md` for detailed troubleshooting
2. Verify ALB is healthy: `terraform output app_url_alb`
3. Check CloudFront status in AWS Console
4. Review CloudWatch logs for errors

## Summary

CloudFront provides the best solution for your requirements:
- ✅ No domain purchase needed
- ✅ Shorter, more memorable URL
- ✅ Free HTTPS encryption
- ✅ Better DNS resolution on mobile
- ✅ Production-ready setup
- ✅ Free tier covers development usage

Deploy now with `.\deploy-cloudfront.ps1` and get your new HTTPS URL in 20 minutes!
