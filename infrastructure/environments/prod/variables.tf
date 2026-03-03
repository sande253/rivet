variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
}

variable "availability_zones" {
  description = "Two AZs within the chosen region."
  type        = list(string)
}

variable "anthropic_api_key" {
  description = "Anthropic API key. Supply via TF_VAR_anthropic_api_key — never commit."
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Docker image tag to deploy (use a git SHA, not 'latest', in prod)."
  type        = string
}

variable "desired_count" {
  description = "Number of ECS tasks to run."
  type        = number
  default     = 2
}
