variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID (required for inference profile ARNs)"
  type        = string
  default     = "976792586595"
}


# ── Networking ────────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.21.0/24", "10.0.22.0/24"]
}

# ── SSL/TLS ───────────────────────────────────────────────────────────────────
variable "domain_name" {
  description = "Domain name for ACM certificate (leave empty to skip HTTPS)"
  type        = string
  default     = ""
}

variable "subject_alternative_names" {
  description = "Additional domain names for ACM certificate"
  type        = list(string)
  default     = []
}

# ── Database ──────────────────────────────────────────────────────────────────
variable "db_name" {
  description = "Database name"
  type        = string
  default     = "rivet"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "rivetadmin"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false  # Set to true for production HA
}

variable "db_backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

# ── Compute ───────────────────────────────────────────────────────────────────
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "min_size" {
  description = "Minimum number of instances"
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum number of instances"
  type        = number
  default     = 6
}

variable "desired_capacity" {
  description = "Desired number of instances"
  type        = number
  default     = 2
}

# ── GenAI Configuration ───────────────────────────────────────────────────────
variable "use_bedrock" {
  description = "Use AWS Bedrock instead of Anthropic API"
  type        = bool
  default     = false  # Use Anthropic API directly - simpler and more reliable
}

variable "anthropic_api_key" {
  description = "Anthropic API key (only if use_bedrock=false)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "draft_model_id" {
  description = "Model ID for draft generation"
  type        = string
  default     = "claude-3-5-sonnet-20241022"
}

variable "critic_model_id" {
  description = "Model ID for critic"
  type        = string
  default     = "claude-3-5-sonnet-20241022"
}

variable "vision_model_id" {
  description = "Model ID for vision analysis"
  type        = string
  default     = "claude-3-5-sonnet-20241022"
}

variable "bedrock_image_model_id" {
  description = "Model ID for image generation"
  type        = string
  default     = "amazon.titan-image-generator-v2:0"
}

# ── Monitoring ────────────────────────────────────────────────────────────────
variable "bedrock_log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "enable_bedrock_alarms" {
  description = "Enable Bedrock CloudWatch alarms"
  type        = bool
  default     = true
}

variable "genai_latency_threshold_ms" {
  description = "Latency threshold for GenAI alarms (ms)"
  type        = number
  default     = 5000
}

variable "genai_error_threshold_count" {
  description = "Error count threshold for GenAI alarms"
  type        = number
  default     = 5
}
