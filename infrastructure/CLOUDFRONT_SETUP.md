# CloudFront Distribution Setup

## Overview

This document explains the CloudFront distribution setup for the Rivet application, providing a shorter AWS URL with HTTPS support.

## Why CloudFront?

### Problem
- ALB DNS name is long: `rivet-dev-alb-734627388.us-east-1.elb.amazonaws.com`
- DNS resolution issues on some mobile networks
- HTTP only (no HTTPS)
- No custom domain available

### Solution: CloudFront
- ✅ Shorter AWS URL: `d1234abcd.cloudfront.net` (example)
- ✅ Free HTTPS with AWS certificate
- ✅ Better DNS propagation globally
- ✅ Edge caching for improved performance
- ✅ No domain purchase required

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CloudFront Distribution                         │
│              d1234abcd.cloudfront.net                        │
│              ├─ Global Edge Locations                        │
│              ├─ Free SSL Certificate                         │
│              └─ Automatic HTTPS redirect                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Load Balancer                       │
│         rivet-dev-alb-734627388.us-east-1.elb...            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              EC2 Auto Scaling Group                          │
│              Docker + Gunicorn + Flask                       │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Details

### CloudFront Settings
- **Price Class**: `PriceClass_100` (North America & Europe only)
- **Origin**: ALB DNS name
- **Protocol**: HTTP to origin, HTTPS to viewers
- **Caching**: Disabled (TTL = 0) for dynamic content
- **Compression**: Enabled
- **IPv6**: Enabled

### Cache Behavior
- **Allowed Methods**: All HTTP methods (GET, POST, PUT, DELETE, etc.)
- **Cached Methods**: GET, HEAD only
- **Query Strings**: Forwarded to origin
- **Cookies**: All forwarded (required for Flask sessions)
- **Headers**: Host, Origin, Referer, User-Agent forwarded

### Security
- **Viewer Protocol**: Redirect HTTP → HTTPS
- **SSL Certificate**: CloudFront default (free)
- **Geo Restrictions**: None

## Deployment Steps

### 1. Apply Terraform Changes

```bash
cd infrastructure/environments/dev
terraform plan
terraform apply
```

This will create:
- CloudFront distribution
- Origin configuration pointing to ALB
- Cache behaviors
- SSL certificate (automatic)

### 2. Wait for Distribution Deployment

CloudFront distributions take 15-20 minutes to deploy globally.

Check status:
```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='rivet-dev CDN'].{Domain:DomainName,Status:Status}" --output table
```

Status will change from `InProgress` → `Deployed`

### 3. Get Your CloudFront URL

After `terraform apply` completes:
```bash
terraform output cloudfront_url
```

Example output:
```
https://d1234abcd.cloudfront.net
```

### 4. Test the URL

```bash
# Test from command line
curl -I https://d1234abcd.cloudfront.net

# Or open in browser
start https://d1234abcd.cloudfront.net
```

### 5. Test on Mobile

Open the CloudFront URL on your mobile phone. It should:
- ✅ Load successfully
- ✅ Use HTTPS (secure connection)
- ✅ Work on mobile networks
- ✅ Show login page

## Benefits

### 1. Shorter URL
- **Before**: `http://rivet-dev-alb-734627388.us-east-1.elb.amazonaws.com`
- **After**: `https://d1234abcd.cloudfront.net`

### 2. HTTPS Support
- Free SSL certificate from AWS
- Automatic HTTP → HTTPS redirect
- Secure password transmission
- Better SEO ranking

### 3. Better DNS Resolution
- CloudFront uses AWS's global DNS infrastructure
- Better propagation to mobile carriers
- More reliable on cellular networks

### 4. Performance
- Edge caching (when enabled)
- Compression enabled
- Global edge locations
- Reduced latency

### 5. No Cost for Low Traffic
- CloudFront free tier: 1TB data transfer out per month
- 10,000,000 HTTP/HTTPS requests per month
- Perfect for development and testing

## Troubleshooting

### Distribution Status: InProgress
**Issue**: CloudFront distribution is still deploying
**Solution**: Wait 15-20 minutes, check status with AWS CLI

### 502 Bad Gateway
**Issue**: CloudFront can't reach ALB
**Solution**: 
- Verify ALB is healthy: `terraform output app_url_alb`
- Check ALB security group allows traffic from 0.0.0.0/0
- Verify EC2 instances are healthy

### Session/Cookie Issues
**Issue**: Login doesn't work through CloudFront
**Solution**: 
- Verify `cookies { forward = "all" }` in cache behavior
- Check Flask session configuration
- Ensure `SESSION_COOKIE_SECURE = False` (or True if using HTTPS)

### Caching Issues
**Issue**: Seeing old content after updates
**Solution**: 
- Current config has caching disabled (TTL = 0)
- If needed, invalidate cache:
```bash
aws cloudfront create-invalidation --distribution-id E1234ABCD --paths "/*"
```

## Cost Considerations

### Free Tier (First 12 Months)
- 1 TB data transfer out
- 10,000,000 HTTP/HTTPS requests
- 2,000,000 CloudFront Function invocations

### After Free Tier
- Data transfer: ~$0.085/GB (first 10TB)
- Requests: ~$0.0075 per 10,000 requests
- Example: 100GB transfer + 1M requests = ~$8.50/month

### Comparison
- **CloudFront**: ~$8.50/month for 100GB + 1M requests
- **ALB**: ~$16/month base + $0.008/LCU-hour
- **Total Savings**: None, but you get HTTPS + better DNS

## Next Steps

### Option 1: Use CloudFront URL (Recommended)
- ✅ Free HTTPS
- ✅ Shorter URL
- ✅ Better DNS resolution
- ✅ No domain purchase needed

### Option 2: Add Custom Domain Later
If you buy a domain (e.g., `rivet.com`):
1. Request ACM certificate for your domain
2. Add custom domain to CloudFront distribution
3. Create Route53 A record pointing to CloudFront
4. Update `viewer_certificate` in Terraform

### Option 3: Use Free Subdomain Service
Services like DuckDNS, FreeDNS, or No-IP:
1. Register free subdomain (e.g., `rivet.duckdns.org`)
2. Point CNAME to CloudFront domain
3. Update CloudFront with custom domain

## Terraform Resources Created

```hcl
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "rivet-dev CDN"
  price_class         = "PriceClass_100"
  
  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-origin"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb-origin"
    
    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Referer", "User-Agent"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }
  
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
```

## Summary

CloudFront provides a production-ready solution for accessing your application with:
- Shorter, more memorable URL
- Free HTTPS encryption
- Better DNS resolution on mobile networks
- Global edge caching
- No domain purchase required

Deploy with `terraform apply` and get your new HTTPS URL in 15-20 minutes.
