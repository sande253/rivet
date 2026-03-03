output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS name (HTTP)"
  value       = aws_lb.main.dns_name
}

output "alb_https_url" {
  description = "ALB HTTPS URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "HTTPS not configured - set domain_name variable"
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = module.database.database_name
}

output "upload_bucket_name" {
  description = "S3 upload bucket name"
  value       = module.storage.upload_bucket_name
}

output "autoscaling_group_name" {
  description = "Auto Scaling Group name"
  value       = module.ec2.autoscaling_group_name
}

output "certificate_arn" {
  description = "ACM certificate ARN"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : "No certificate created"
}

output "certificate_validation_records" {
  description = "DNS records for certificate validation"
  value = var.domain_name != "" ? [
    for dvo in aws_acm_certificate.main[0].domain_validation_options : {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
    }
  ] : []
}

output "deployment_instructions" {
  description = "Next steps for deployment"
  value = <<-EOT
    
    ═══════════════════════════════════════════════════════════════
    Production Deployment Complete
    ═══════════════════════════════════════════════════════════════
    
    1. Build and push Docker image:
       aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.app.repository_url}
       cd application
       docker build -t ${aws_ecr_repository.app.repository_url}:latest .
       docker push ${aws_ecr_repository.app.repository_url}:latest
    
    2. ${var.domain_name != "" ? "Configure DNS for HTTPS:\n       Add the following DNS records to validate the certificate:\n       ${join("\n       ", [for dvo in aws_acm_certificate.main[0].domain_validation_options : "${dvo.resource_record_name} ${dvo.resource_record_type} ${dvo.resource_record_value}"])}\n\n       Then point your domain to the ALB:\n       ${var.domain_name} CNAME ${aws_lb.main.dns_name}" : "Access via HTTP:\n       http://${aws_lb.main.dns_name}"}
    
    3. Trigger instance refresh:
       aws autoscaling start-instance-refresh --auto-scaling-group-name ${module.ec2.autoscaling_group_name}
    
    4. Monitor deployment:
       aws autoscaling describe-instance-refreshes --auto-scaling-group-name ${module.ec2.autoscaling_group_name} --max-records 1
    
    5. Check application logs:
       aws logs tail /ec2/${local.project_name}-${local.environment} --follow
    
    ═══════════════════════════════════════════════════════════════
  EOT
}
