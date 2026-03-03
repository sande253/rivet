# ── Outputs ───────────────────────────────────────────────────────────────────
output "app_url" {
  description = "Public URL of the application (CloudFront with HTTPS)."
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "app_url_alb" {
  description = "Direct ALB URL (HTTP only, for debugging)."
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR URL — push your Docker image here before deploying."
  value       = aws_ecr_repository.app.repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID (for Route53)"
  value       = aws_lb.main.zone_id
}

output "autoscaling_group_name" {
  description = "Auto Scaling Group name"
  value       = module.ec2.autoscaling_group_name
}

output "s3_bucket_name" {
  description = "S3 bucket name for uploaded product images."
  value       = module.storage.upload_bucket_name
}

output "vpc_id" {
  description = "VPC ID."
  value       = module.networking.vpc_id
}

output "anthropic_secret_name" {
  description = "Secrets Manager secret name for Anthropic API key."
  value       = module.secrets.secret_name
}

output "draft_model_parameter" {
  description = "SSM parameter name for draft model ID."
  value       = module.secrets.draft_model_parameter_name
}

output "critic_model_parameter" {
  description = "SSM parameter name for critic model ID."
  value       = module.secrets.critic_model_parameter_name
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name (shorter AWS URL with HTTPS)."
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_url" {
  description = "Full CloudFront URL with HTTPS."
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}
