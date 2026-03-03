variable "project_name" {
  description = "Short identifier used as a prefix for all resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev | prod)."
  type        = string
}

variable "aws_region" {
  description = "AWS region where resources are deployed."
  type        = string
}

# ── Network (from networking module) ─────────────────────────────────────────
variable "vpc_id" {
  description = "ID of the VPC."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for the Application Load Balancer."
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks."
  type        = string
}

# ── Secrets (from secrets module) ────────────────────────────────────────────
variable "anthropic_secret_arn" {
  description = "ARN of the Anthropic API key in Secrets Manager."
  type        = string
}

variable "read_secret_policy_arn" {
  description = "ARN of the IAM policy granting access to the Anthropic secret."
  type        = string
}

# ── Storage (from storage module) ────────────────────────────────────────────
variable "upload_bucket_name" {
  description = "Name of the S3 bucket for uploaded product images."
  type        = string
}

variable "upload_bucket_arn" {
  description = "ARN of the S3 bucket (used in IAM policy)."
  type        = string
}

# ── Container configuration ───────────────────────────────────────────────────
variable "container_port" {
  description = "Port the Flask/Gunicorn container listens on."
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)."
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate task memory in MB."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of running ECS tasks."
  type        = number
  default     = 1
}

variable "image_tag" {
  description = "Docker image tag to deploy (e.g. 'latest' or a git SHA)."
  type        = string
  default     = "latest"
}

# ── Bedrock & GenAI configuration ─────────────────────────────────────────────
variable "bedrock_invoke_policy_arn" {
  description = "ARN of the IAM policy granting Bedrock model invocation permissions."
  type        = string
}

variable "read_ssm_policy_arn" {
  description = "ARN of the IAM policy granting access to SSM parameters."
  type        = string
}

variable "draft_model_id" {
  description = "Bedrock model ID for draft tip generation."
  type        = string
}

variable "critic_model_id" {
  description = "Bedrock model ID for quality evaluation."
  type        = string
}

variable "vision_model_id" {
  description = "Bedrock model ID for vision assist (optional)."
  type        = string
}

variable "bedrock_image_model_id" {
  description = "Bedrock model ID for mockup image generation."
  type        = string
}
