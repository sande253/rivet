# SSL Certificate and HTTPS Configuration for rivetai.online

# Request SSL certificate from AWS Certificate Manager (FREE)
resource "aws_acm_certificate" "rivet_ssl" {
  domain_name       = "rivetai.online"
  validation_method = "DNS"

  subject_alternative_names = [
    "www.rivetai.online"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "rivet-ssl-certificate"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# DNS validation records (you'll need to add these to GoDaddy)
output "ssl_validation_records" {
  description = "Add these CNAME records to GoDaddy for SSL validation"
  value = {
    for dvo in aws_acm_certificate.rivet_ssl.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
    }
  }
}

# Wait for certificate validation
resource "aws_acm_certificate_validation" "rivet_ssl" {
  certificate_arn = aws_acm_certificate.rivet_ssl.arn

  timeouts {
    create = "45m"
  }
}

# Get existing load balancer
data "aws_lb" "rivet_alb" {
  name = "rivet-prod-alb"
}

# Get existing target group
data "aws_lb_target_group" "rivet_tg" {
  name = "rivet-prod-tg"
}

# Add HTTPS listener to load balancer
resource "aws_lb_listener" "https" {
  load_balancer_arn = data.aws_lb.rivet_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.rivet_ssl.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = data.aws_lb_target_group.rivet_tg.arn
  }

  tags = {
    Name        = "rivet-https-listener"
    Environment = "production"
  }
}

# Update HTTP listener to redirect to HTTPS
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = data.aws_lb.rivet_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = {
    Name        = "rivet-http-redirect"
    Environment = "production"
  }
}

# Output the final URLs
output "website_urls" {
  description = "Your website URLs"
  value = {
    http_url  = "http://rivetai.online (redirects to HTTPS)"
    https_url = "https://rivetai.online"
    www_url   = "https://www.rivetai.online"
  }
}

output "certificate_status" {
  description = "SSL certificate status"
  value       = aws_acm_certificate.rivet_ssl.status
}
