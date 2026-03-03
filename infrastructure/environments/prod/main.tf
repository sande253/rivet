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
    key     = "tf-state/prod/terraform.tfstate"
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
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# ── Local variables ───────────────────────────────────────────────────────────
locals {
  project_name = "rivet"
  environment  = "prod"
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
  database_subnet_cidrs = var.database_subnet_cidrs
  
  enable_nat_gateway = true
  single_nat_gateway = false  # Multi-AZ NAT for production HA
}

# ── Storage Module ────────────────────────────────────────────────────────────
module "storage" {
  source = "../../modules/storage"

  project_name = local.project_name
  environment  = local.environment
}

# ── Database Module (RDS PostgreSQL) ──────────────────────────────────────────
module "database" {
  source = "../../modules/database"

  project_name = local.project_name
  environment  = local.environment

  vpc_id                = module.networking.vpc_id
  database_subnet_ids   = module.networking.database_subnet_ids
  ec2_security_group_id = ""  # Will be added after EC2 module creates SG

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  multi_az              = var.db_multi_az
  backup_retention_days = var.db_backup_retention_days
  
  database_name = var.db_name
  master_username = var.db_username
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
  
  # Store database credentials
  db_host     = module.database.address
  db_port     = module.database.port
  db_name     = var.db_name
  db_username = var.db_username
  db_password = module.database.password
}

# ── Bedrock Module ────────────────────────────────────────────────────────────
module "bedrock" {
  source = "../../modules/bedrock"

  project_name = local.project_name
  environment  = local.environment
  aws_region   = var.aws_region

  app_log_group_name    = "/ec2/${local.project_name}-${local.environment}"
  create_metric_filters = false  # Enable after first deployment
  log_retention_days    = var.bedrock_log_retention_days
  enable_alarms         = var.enable_bedrock_alarms
  latency_threshold_ms  = var.genai_latency_threshold_ms
  error_threshold_count = var.genai_error_threshold_count
}

# ── ECR Repository ────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "app" {
  name                 = "${local.project_name}-${local.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
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
        description  = "Retain only the last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

# ── ACM Certificate ───────────────────────────────────────────────────────────
resource "aws_acm_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0
  
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = var.subject_alternative_names

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${local.project_name}-${local.environment}-cert"
    Environment = local.environment
    Project     = local.project_name
  }
}

# ── Application Load Balancer ─────────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "${local.project_name}-${local.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [module.networking.alb_security_group_id]
  subnets            = module.networking.public_subnet_ids

  enable_deletion_protection = true
  enable_http2               = true
  enable_cross_zone_load_balancing = true

  access_logs {
    bucket  = module.storage.alb_logs_bucket_name
    enabled = true
  }

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

  deregistration_delay = 30

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }

  tags = {
    Environment = local.environment
    Project     = local.project_name
  }
}

# HTTP Listener - Forward to target group if no domain, otherwise redirect to HTTPS
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = var.domain_name != "" ? "redirect" : "forward"
    
    target_group_arn = var.domain_name != "" ? null : aws_lb_target_group.app.arn
    
    dynamic "redirect" {
      for_each = var.domain_name != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.domain_name != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# ── EC2 Module ────────────────────────────────────────────────────────────────
module "ec2" {
  source = "../../modules/ec2_prod"

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
  anthropic_secret_arn      = module.secrets.secret_arn
  read_secret_policy_arn    = module.secrets.read_secret_policy_arn
  read_db_secret_policy_arn = module.secrets.read_db_secret_policy_arn
  read_ssm_policy_arn       = module.secrets.read_ssm_policy_arn

  # Storage
  upload_bucket_name = module.storage.upload_bucket_name
  upload_bucket_arn  = module.storage.upload_bucket_arn

  # Database
  db_secret_arn = module.secrets.db_secret_arn

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

  depends_on = [
    aws_ecr_repository.app,
    module.database
  ]
}

# ── CloudWatch Alarms ─────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_target_response_time" {
  alarm_name          = "${local.project_name}-${local.environment}-alb-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 2.0
  alarm_description   = "Alert when ALB target response time exceeds 2 seconds"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "${local.project_name}-${local.environment}-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when there are unhealthy hosts"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.app.arn_suffix
  }
}
