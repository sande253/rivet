variable "project_name" {
  description = "Short identifier used as a prefix for all resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev | prod)."
  type        = string
}
