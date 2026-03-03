variable "project_name" {
  description = "Short identifier used as a prefix for all resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev | prod)."
  type        = string
}

variable "anthropic_api_key" {
  description = <<-EOT
    Your Anthropic API key.
    Supply this via TF_VAR_anthropic_api_key environment variable — never
    hard-code it or commit it to version control.
  EOT
  type        = string
  sensitive   = true
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

variable "db_host" {
  description = "Database host (RDS endpoint)"
  type        = string
  default     = "placeholder"
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "rivet"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "rivetadmin"
}

variable "db_password" {
  description = "Database password"
  type        = string
  default     = "placeholder"
  sensitive   = true
}
