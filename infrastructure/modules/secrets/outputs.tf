output "secret_arn" {
  description = "ARN of the Anthropic API key secret in Secrets Manager."
  value       = aws_secretsmanager_secret.anthropic_api_key.arn
}

output "secret_name" {
  description = "Name of the Anthropic API key secret."
  value       = aws_secretsmanager_secret.anthropic_api_key.name
}

output "read_secret_policy_arn" {
  description = "ARN of the IAM policy that allows reading the Anthropic secret."
  value       = aws_iam_policy.read_anthropic_secret.arn
}

output "read_ssm_policy_arn" {
  description = "ARN of the IAM policy that grants read access to SSM parameters."
  value       = aws_iam_policy.read_ssm_parameters.arn
}

output "draft_model_parameter_name" {
  description = "SSM parameter name for draft model ID."
  value       = aws_ssm_parameter.draft_model_id.name
}

output "critic_model_parameter_name" {
  description = "SSM parameter name for critic model ID."
  value       = aws_ssm_parameter.critic_model_id.name
}

output "vision_model_parameter_name" {
  description = "SSM parameter name for vision model ID (empty if vision is disabled)."
  value       = length(aws_ssm_parameter.vision_model_id) > 0 ? aws_ssm_parameter.vision_model_id[0].name : ""
}

output "bedrock_image_model_parameter_name" {
  description = "SSM parameter name for Bedrock image model ID."
  value       = aws_ssm_parameter.bedrock_image_model_id.name
}

output "db_secret_arn" {
  description = "ARN of the database credentials secret (empty if no database)"
  value       = length(aws_secretsmanager_secret.database) > 0 ? aws_secretsmanager_secret.database[0].arn : ""
}

output "db_secret_name" {
  description = "Name of the database credentials secret (empty if no database)"
  value       = length(aws_secretsmanager_secret.database) > 0 ? aws_secretsmanager_secret.database[0].name : ""
}
