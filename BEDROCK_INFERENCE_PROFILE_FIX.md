# Bedrock Inference Profile Fix

## Issue
The analysis endpoint was returning "Internal server error" due to an AccessDeniedException when trying to invoke Bedrock models using cross-region inference profiles.

## Root Cause
AWS Bedrock now requires using inference profiles (e.g., `us.anthropic.claude-3-5-sonnet-20241022-v2:0`) instead of direct model IDs. The IAM policy only allowed access to `foundation-model/*` resources, but inference profiles use a different ARN format: `inference-profile/*`.

## Error Message
```
User: arn:aws:sts::976792586595:assumed-role/rivet-prod-ec2-role/i-000ef45c39f475934 
is not authorized to perform: bedrock:InvokeModel on resource: 
arn:aws:bedrock:us-east-1:976792586595:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0 
because no identity-based policy allows the bedrock:InvokeModel action
```

## Solution
Updated the Bedrock IAM policy to include inference profile ARN patterns:

### Changes Made

1. **Updated `infrastructure/modules/bedrock/main.tf`**:
   - Added inference profile ARN patterns to the Bedrock IAM policy:
     ```hcl
     # Cross-region inference profiles (required for us.anthropic.* model IDs)
     "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:inference-profile/us.anthropic.claude-*",
     "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:inference-profile/anthropic.claude-*",
     ```

2. **Added `aws_account_id` variable**:
   - Added to `infrastructure/modules/bedrock/variables.tf`
   - Added to `infrastructure/environments/prod/variables.tf` with default value `976792586595`
   - Passed from `infrastructure/environments/prod/main.tf` to the Bedrock module

3. **Applied Terraform changes**:
   - Updated the IAM policy in production
   - Triggered instance refresh to replace EC2 instances with updated IAM permissions

## Deployment Steps

1. Updated Terraform configuration
2. Applied changes: `terraform apply`
3. Started instance refresh: `aws autoscaling start-instance-refresh --auto-scaling-group-name rivet-prod-asg`
4. Waited for new instances to become healthy (completed successfully)

## Current Status

✅ IAM policy updated to support inference profiles
✅ Instance refresh completed successfully
✅ Both new instances (i-0d06e4322d32b589e, i-046da52aa594935fd) are healthy
✅ No errors in recent logs
✅ Changes committed and pushed to GitHub

## Testing

The user should now test the analysis endpoint to confirm it works:
1. Navigate to http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/dashboard
2. Upload a sketch and run analysis
3. Verify that the analysis completes successfully without errors

## Related Files

- `infrastructure/modules/bedrock/main.tf` - IAM policy definition
- `infrastructure/modules/bedrock/variables.tf` - Added aws_account_id variable
- `infrastructure/environments/prod/main.tf` - Bedrock module configuration
- `infrastructure/environments/prod/variables.tf` - Added aws_account_id variable
- `application/src/services/bedrock_client.py` - Model ID mapping (already updated in previous fix)
