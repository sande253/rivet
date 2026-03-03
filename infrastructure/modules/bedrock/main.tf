locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ── CloudWatch Log Group for Bedrock model invocations ────────────────────────
resource "aws_cloudwatch_log_group" "bedrock" {
  name              = "/aws/bedrock/${local.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${local.name_prefix}-bedrock-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── IAM Policy for Bedrock model invocation ───────────────────────────────────
resource "aws_iam_policy" "bedrock_invoke" {
  name        = "${local.name_prefix}-bedrock-invoke"
  description = "Allows ECS tasks to invoke Bedrock foundation models for AI analysis."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockModelInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = [
          # Anthropic Claude models
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-haiku-*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-5-sonnet-*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-opus-*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-*",
          # Amazon Titan models
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-*",
        ]
      },
      {
        Sid    = "BedrockModelList"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.bedrock.arn}:*"
      }
    ]
  })

  tags = {
    Name        = "${local.name_prefix}-bedrock-policy"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ── CloudWatch Metrics for GenAI telemetry ────────────────────────────────────
# Note: These metric filters depend on the app log group being created first
# The log group is created by the compute module, so we add a lifecycle rule
# to create these after the log group exists

resource "aws_cloudwatch_log_metric_filter" "genai_latency" {
  count = var.create_metric_filters ? 1 : 0

  name           = "${local.name_prefix}-genai-latency"
  log_group_name = var.app_log_group_name
  pattern        = "[time, request_id, level, msg=\"GenAI*\", latency_ms]"

  metric_transformation {
    name      = "GenAILatencyMs"
    namespace = "Rivet/${var.environment}"
    value     = "$latency_ms"
    unit      = "Milliseconds"
  }
}

resource "aws_cloudwatch_log_metric_filter" "genai_errors" {
  count = var.create_metric_filters ? 1 : 0

  name           = "${local.name_prefix}-genai-errors"
  log_group_name = var.app_log_group_name
  pattern        = "[time, request_id, level=ERROR, msg=\"GenAI*\"]"

  metric_transformation {
    name      = "GenAIErrors"
    namespace = "Rivet/${var.environment}"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "circuit_breaker_open" {
  count = var.create_metric_filters ? 1 : 0

  name           = "${local.name_prefix}-circuit-breaker-open"
  log_group_name = var.app_log_group_name
  pattern        = "[time, request_id, level, msg=\"*circuit breaker OPEN*\"]"

  metric_transformation {
    name      = "CircuitBreakerOpen"
    namespace = "Rivet/${var.environment}"
    value     = "1"
    unit      = "Count"
  }
}

# ── CloudWatch Alarms for GenAI health ────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "genai_high_latency" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-genai-high-latency"
  alarm_description   = "GenAI latency exceeds threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GenAILatencyMs"
  namespace           = "Rivet/${var.environment}"
  period              = 300
  statistic           = "Average"
  threshold           = var.latency_threshold_ms
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${local.name_prefix}-genai-latency-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "genai_error_rate" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${local.name_prefix}-genai-error-rate"
  alarm_description   = "GenAI error rate exceeds threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GenAIErrors"
  namespace           = "Rivet/${var.environment}"
  period              = 300
  statistic           = "Sum"
  threshold           = var.error_threshold_count
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${local.name_prefix}-genai-error-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}
