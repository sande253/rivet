terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "tf-rivet-project-bucket"
    key     = "tf-state/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
    # dynamodb_table = "rivet-terraform-locks"  # Uncomment for state locking
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rivet"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# ── Local variables ───────────────────────────────────────────────────────────
locals {
  project_name = "rivet"
  environment  = "dev"
}

# ── Storage Module ────────────────────────────────────────────────────────────
module "storage" {
  source = "../../modules/storage"

  project_name = local.project_name
  environment  = local.environment
}

# ── Secrets Module ────────────────────────────────────────────────────────────
module "secrets" {
  source = "../../modules/secrets"

  project_name = local.project_name
  environment  = local.environment

  anthropic_api_key      = var.anthropic_api_key
  draft_model_id         = var.draft_model_id
  critic_model_id        = var.critic_model_id
  vision_model_id        = var.vision_model_id
  bedrock_image_model_id = var.bedrock_image_model_id
}

# ── Networking Module ─────────────────────────────────────────────────────────
module "networking" {
  source = "../../modules/networking"

  project_name = local.project_name
  environment  = local.environment

  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# ── Bedrock Module ────────────────────────────────────────────────────────────
module "bedrock" {
  source = "../../modules/bedrock"

  project_name = local.project_name
  environment  = local.environment
  aws_region   = var.aws_region

  # EC2 will log to this group
  app_log_group_name = "/ec2/${local.project_name}-${local.environment}"

  # Disable metric filters initially since log group doesn't exist yet
  # Enable after first apply by setting this to true
  create_metric_filters = false

  log_retention_days    = var.bedrock_log_retention_days
  enable_alarms         = var.enable_bedrock_alarms
  latency_threshold_ms  = var.genai_latency_threshold_ms
  error_threshold_count = var.genai_error_threshold_count
}

# ── ECR Repository (for Docker images) ────────────────────────────────────────
resource "aws_ecr_repository" "app" {
  name                 = "${local.project_name}-${local.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${local.project_name}-${local.environment}"
    Environment = local.environment
    Project     = local.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain only the last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = { type = "expire" }
      }
    ]
  })
}

# ── Application Load Balancer ─────────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "${local.project_name}-${local.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.networking.alb_security_group_id]
  subnets            = module.networking.public_subnet_ids

  enable_deletion_protection = false

  tags = {
    Name        = "${local.project_name}-${local.environment}-alb"
    Environment = local.environment
    Project     = local.project_name
  }
}

resource "aws_lb_target_group" "app" {
  name        = "${local.project_name}-${local.environment}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = module.networking.vpc_id
  target_type = "instance"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200,302"
  }

  tags = {
    Environment = local.environment
    Project     = local.project_name
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ── EC2 Module ────────────────────────────────────────────────────────────────
module "ec2" {
  source = "../../modules/ec2"

  project_name = local.project_name
  environment  = local.environment
  aws_region   = var.aws_region

  # Networking
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  alb_security_group_id  = module.networking.alb_security_group_id
  target_group_arn       = aws_lb_target_group.app.arn

  # ECR
  ecr_repository_url = aws_ecr_repository.app.repository_url
  image_tag          = var.image_tag

  # Secrets
  anthropic_secret_arn   = module.secrets.secret_arn
  read_secret_policy_arn = module.secrets.read_secret_policy_arn
  read_ssm_policy_arn    = module.secrets.read_ssm_policy_arn

  # Storage
  upload_bucket_name = module.storage.upload_bucket_name
  upload_bucket_arn  = module.storage.upload_bucket_arn

  # Bedrock
  bedrock_invoke_policy_arn = module.bedrock.bedrock_invoke_policy_arn

  # GenAI model configuration
  use_bedrock            = var.use_bedrock
  draft_model_id         = var.draft_model_id
  critic_model_id        = var.critic_model_id
  vision_model_id        = var.vision_model_id
  bedrock_image_model_id = var.bedrock_image_model_id

  # Instance configuration
  instance_type    = var.instance_type
  container_port   = var.container_port
  min_size         = var.min_size
  max_size         = var.max_size
  desired_capacity = var.desired_capacity

  # Ensure ECR repository exists before EC2 tries to pull
  depends_on = [aws_ecr_repository.app]
}

# ── CloudFront Distribution ───────────────────────────────────────────────────
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.project_name}-${local.environment} CDN"
  price_class         = "PriceClass_100"  # Use only North America and Europe edge locations

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb-origin"

    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Referer", "User-Agent"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "${local.project_name}-${local.environment}-cdn"
    Environment = local.environment
    Project     = local.project_name
  }
}
