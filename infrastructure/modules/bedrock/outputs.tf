output "bedrock_invoke_policy_arn" {
  description = "ARN of the IAM policy that grants Bedrock model invocation permissions."
  value       = aws_iam_policy.bedrock_invoke.arn
}

output "bedrock_log_group_name" {
  description = "CloudWatch log group name for Bedrock invocations."
  value       = aws_cloudwatch_log_group.bedrock.name
}

output "bedrock_log_group_arn" {
  description = "ARN of the CloudWatch log group for Bedrock invocations."
  value       = aws_cloudwatch_log_group.bedrock.arn
}
