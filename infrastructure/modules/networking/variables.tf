variable "project_name" {
  description = "Short identifier used as a prefix for all resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev | prod)."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two CIDR blocks for public subnets (one per AZ). Host the ALB."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Two CIDR blocks for private subnets (one per AZ). Host ECS tasks."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "availability_zones" {
  description = "Two AZs to spread resources across."
  type        = list(string)
}
