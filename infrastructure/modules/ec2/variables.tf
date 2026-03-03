variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# ── Networking ────────────────────────────────────────────────────────────────
variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EC2 instances"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ALB security group ID"
  type        = string
}

# ── Load Balancer ─────────────────────────────────────────────────────────────
variable "target_group_arn" {
  description = "ALB target group ARN"
  type        = string
}

# ── ECR ───────────────────────────────────────────────────────────────────────
variable "ecr_repository_url" {
  description = "ECR repository URL"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

# ── Secrets ───────────────────────────────────────────────────────────────────
variable "anthropic_secret_arn" {
  description = "Anthropic API key secret ARN"
  type        = string
}

variable "read_secret_policy_arn" {
  description = "IAM policy ARN for reading secrets"
  type        = string
}

variable "read_ssm_policy_arn" {
  description = "IAM policy ARN for reading SSM parameters"
  type        = string
}

# ── Bedrock ───────────────────────────────────────────────────────────────────
variable "bedrock_invoke_policy_arn" {
  description = "IAM policy ARN for Bedrock invocation"
  type        = string
}

# ── Storage ───────────────────────────────────────────────────────────────────
variable "upload_bucket_name" {
  description = "S3 bucket name for uploads"
  type        = string
}

variable "upload_bucket_arn" {
  description = "S3 bucket ARN for uploads"
  type        = string
}

# ── GenAI Configuration ───────────────────────────────────────────────────────
variable "use_bedrock" {
  description = "Use AWS Bedrock instead of Anthropic API"
  type        = bool
  default     = true
}

variable "draft_model_id" {
  description = "Bedrock draft model ID"
  type        = string
}

variable "critic_model_id" {
  description = "Bedrock critic model ID"
  type        = string
}

variable "vision_model_id" {
  description = "Bedrock vision model ID"
  type        = string
}

variable "bedrock_image_model_id" {
  description = "Bedrock image generation model ID"
  type        = string
}

# ── Instance Configuration ────────────────────────────────────────────────────
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────
variable "min_size" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Desired number of instances"
  type        = number
  default     = 1
}
