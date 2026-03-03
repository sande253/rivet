# ── Core Configuration ────────────────────────────────────────────────────────
variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
}

variable "availability_zones" {
  description = "Two AZs within the chosen region."
  type        = list(string)
}

# ── Secrets ───────────────────────────────────────────────────────────────────
variable "anthropic_api_key" {
  description = "Anthropic API key. Supply via TF_VAR_anthropic_api_key — never commit."
  type        = string
  sensitive   = true
}

# ── Networking ────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (ALB)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (ECS tasks)."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ── GenAI Model Configuration ─────────────────────────────────────────────────
variable "use_bedrock" {
  description = "Use AWS Bedrock instead of Anthropic API (recommended for production)."
  type        = bool
  default     = true
}

variable "draft_model_id" {
  description = "Bedrock model ID for draft tip generation (fast/cheap)."
  type        = string
  default     = "anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "critic_model_id" {
  description = "Bedrock model ID for quality evaluation (high-stakes)."
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "vision_model_id" {
  description = "Bedrock model ID for vision assist (optional, empty to disable)."
  type        = string
  default     = ""
}

variable "bedrock_image_model_id" {
  description = "Bedrock model ID for mockup image generation."
  type        = string
  default     = "amazon.titan-image-generator-v2:0"
}

# ── Bedrock Observability ─────────────────────────────────────────────────────
variable "bedrock_log_retention_days" {
  description = "Number of days to retain Bedrock logs."
  type        = number
  default     = 14
}

variable "enable_bedrock_alarms" {
  description = "Whether to create CloudWatch alarms for GenAI metrics."
  type        = bool
  default     = true
}

variable "genai_latency_threshold_ms" {
  description = "Latency threshold in milliseconds for GenAI alarm."
  type        = number
  default     = 5000
}

variable "genai_error_threshold_count" {
  description = "Error count threshold for GenAI alarm (per 5 minutes)."
  type        = number
  default     = 10
}

# ── Container Configuration ───────────────────────────────────────────────────
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
  description = "Docker image tag to deploy."
  type        = string
  default     = "latest"
}


# ── EC2 Configuration ─────────────────────────────────────────────────────────
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "min_size" {
  description = "Minimum number of EC2 instances in Auto Scaling Group"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of EC2 instances in Auto Scaling Group"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Desired number of EC2 instances"
  type        = number
  default     = 1
}
