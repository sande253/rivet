variable "project_name" {
  description = "Project name prefix for all resources."
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
}

variable "aws_region" {
  description = "AWS region where Bedrock models are available."
  type        = string
}

variable "app_log_group_name" {
  description = "CloudWatch log group name for the application (for metric filters)."
  type        = string
}

variable "create_metric_filters" {
  description = "Whether to create metric filters (requires log group to exist first)."
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Number of days to retain Bedrock logs."
  type        = number
  default     = 14
}

variable "enable_alarms" {
  description = "Whether to create CloudWatch alarms for GenAI metrics."
  type        = bool
  default     = true
}

variable "latency_threshold_ms" {
  description = "Latency threshold in milliseconds for GenAI alarm."
  type        = number
  default     = 5000
}

variable "error_threshold_count" {
  description = "Error count threshold for GenAI alarm (per 5 minutes)."
  type        = number
  default     = 10
}

variable "aws_account_id" {
  description = "AWS account ID (required for inference profile ARNs)."
  type        = string
}
