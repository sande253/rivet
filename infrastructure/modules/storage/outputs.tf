output "upload_bucket_name" {
  description = "Name of the S3 bucket for uploaded product images."
  value       = aws_s3_bucket.uploads.id
}

output "upload_bucket_arn" {
  description = "ARN of the S3 uploads bucket (used in IAM policies)."
  value       = aws_s3_bucket.uploads.arn
}

output "alb_logs_bucket_name" {
  description = "Name of the S3 bucket for ALB access logs."
  value       = aws_s3_bucket.alb_logs.id
}

output "alb_logs_bucket_arn" {
  description = "ARN of the ALB logs bucket."
  value       = aws_s3_bucket.alb_logs.arn
}
