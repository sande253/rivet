terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state — configure before first apply
  backend "s3" {
    bucket         = "rivet-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "rivet-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rivet"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# ── Networking ────────────────────────────────────────────────────────────────
module "networking" {
  source = "../../modules/networking"

  project_name       = "rivet"
  environment        = "prod"
  availability_zones = var.availability_zones
}

# ── Storage ───────────────────────────────────────────────────────────────────
module "storage" {
  source = "../../modules/storage"

  project_name = "rivet"
  environment  = "prod"
}

# ── Secrets ───────────────────────────────────────────────────────────────────
module "secrets" {
  source = "../../modules/secrets"

  project_name      = "rivet"
  environment       = "prod"
  anthropic_api_key = var.anthropic_api_key
}

# ── Compute ───────────────────────────────────────────────────────────────────
module "compute" {
  source = "../../modules/compute"

  project_name = "rivet"
  environment  = "prod"
  aws_region   = var.aws_region

  # From networking
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  ecs_security_group_id = module.networking.ecs_security_group_id

  # From secrets
  anthropic_secret_arn   = module.secrets.secret_arn
  read_secret_policy_arn = module.secrets.read_secret_policy_arn

  # From storage
  upload_bucket_name = module.storage.upload_bucket_name
  upload_bucket_arn  = module.storage.upload_bucket_arn

  # Prod sizing — 1 vCPU, 2 GB, 2 replicas for availability
  cpu           = 1024
  memory        = 2048
  desired_count = var.desired_count
  image_tag     = var.image_tag
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "app_url" {
  description = "Public URL of the application (ALB DNS). Point your domain CNAME here."
  value       = "http://${module.compute.alb_dns_name}"
}

output "ecr_repository_url" {
  description = "ECR URL — push your Docker image here before deploying."
  value       = module.compute.ecr_repository_url
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for application logs."
  value       = module.compute.cloudwatch_log_group
}
