locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ── AWS Secrets Manager — Anthropic API key ───────────────────────────────────
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "${local.name_prefix}/anthropic-api-key"
  description = "Anthropic API key for the Rivet product viability analyzer."

  # Prevent accidental deletion
  recovery_window_in_days = 7

  tags = {
    Name        = "${local.name_prefix}-anthropic-key"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# ── SSM Parameters for GenAI model configuration ──────────────────────────────
resource "aws_ssm_parameter" "draft_model_id" {
  name        = "/${local.name_prefix}/genai/draft-model-id"
  description = "Bedrock model ID for draft tip generation (fast/cheap)"
  type        = "String"
  value       = var.draft_model_id

  tags = {
    Name        = "${local.name_prefix}-draft-model"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ssm_parameter" "critic_model_id" {
  name        = "/${local.name_prefix}/genai/critic-model-id"
  description = "Bedrock model ID for quality evaluation (high-stakes)"
  type        = "String"
  value       = var.critic_model_id

  tags = {
    Name        = "${local.name_prefix}-critic-model"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ssm_parameter" "vision_model_id" {
  count = var.vision_model_id != "" ? 1 : 0

  name        = "/${local.name_prefix}/genai/vision-model-id"
  description = "Bedrock model ID for vision assist (optional)"
  type        = "String"
  value       = var.vision_model_id

  tags = {
    Name        = "${local.name_prefix}-vision-model"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ssm_parameter" "bedrock_image_model_id" {
  name        = "/${local.name_prefix}/genai/bedrock-image-model-id"
  description = "Bedrock model ID for mockup image generation"
  type        = "String"
  value       = var.bedrock_image_model_id

  tags = {
    Name        = "${local.name_prefix}-bedrock-image-model"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── IAM policy — allows ECS tasks to read secrets ─────────────────────────────
resource "aws_iam_policy" "read_anthropic_secret" {
  name        = "${local.name_prefix}-read-anthropic-secret"
  description = "Grants read access to the Anthropic API key secret."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = aws_secretsmanager_secret.anthropic_api_key.arn
      }
    ]
  })
}

# ── IAM policy — allows ECS tasks to read SSM parameters ──────────────────────
resource "aws_iam_policy" "read_ssm_parameters" {
  name        = "${local.name_prefix}-read-ssm-parameters"
  description = "Grants read access to GenAI model configuration parameters."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
        ]
        Resource = concat(
          [
            aws_ssm_parameter.draft_model_id.arn,
            aws_ssm_parameter.critic_model_id.arn,
            aws_ssm_parameter.bedrock_image_model_id.arn,
          ],
          length(aws_ssm_parameter.vision_model_id) > 0 ? [aws_ssm_parameter.vision_model_id[0].arn] : []
        )
      }
    ]
  })
}
