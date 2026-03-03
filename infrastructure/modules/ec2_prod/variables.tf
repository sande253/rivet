variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ALB security group ID"
  type        = string
}

variable "target_group_arn" {
  description = "Target group ARN"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
}

variable "anthropic_secret_arn" {
  description = "Anthropic API key secret ARN"
  type        = string
}

variable "db_secret_arn" {
  description = "Database credentials secret ARN"
  type        = string
  default     = ""
}

variable "read_secret_policy_arn" {
  description = "IAM policy ARN for reading secrets"
  type        = string
}

variable "read_db_secret_policy_arn" {
  description = "IAM policy ARN for reading the database credentials secret"
  type        = string
}

variable "read_ssm_policy_arn" {
  description = "IAM policy ARN for reading SSM parameters"
  type        = string
}

variable "upload_bucket_name" {
  description = "S3 upload bucket name"
  type        = string
}

variable "upload_bucket_arn" {
  description = "S3 upload bucket ARN"
  type        = string
}

variable "bedrock_invoke_policy_arn" {
  description = "Bedrock invoke policy ARN"
  type        = string
}

variable "use_bedrock" {
  description = "Use AWS Bedrock instead of Anthropic API"
  type        = bool
}

variable "draft_model_id" {
  description = "Model ID for draft generation"
  type        = string
}

variable "critic_model_id" {
  description = "Model ID for critic"
  type        = string
}

variable "vision_model_id" {
  description = "Model ID for vision analysis"
  type        = string
}

variable "bedrock_image_model_id" {
  description = "Model ID for image generation"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "container_port" {
  description = "Container port"
  type        = number
}

variable "min_size" {
  description = "Minimum number of instances"
  type        = number
}

variable "max_size" {
  description = "Maximum number of instances"
  type        = number
}

variable "desired_capacity" {
  description = "Desired number of instances"
  type        = number
}
