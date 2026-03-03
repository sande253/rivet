# AWS Bedrock Migration Guide

This guide explains the migration from Anthropic API to AWS Bedrock for Claude model access.

## Overview

### What Changed

**Before (Anthropic API)**:
- Direct API calls to Anthropic
- API key stored in Secrets Manager
- Billed by Anthropic
- Model IDs: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`

**After (AWS Bedrock)**:
- API calls through AWS Bedrock
- IAM role authentication (no API keys)
- Billed by AWS
- Model IDs: `anthropic.claude-3-5-sonnet-20241022-v2:0`, etc.

### Benefits

1. **No API Keys**: Uses IAM role credentials automatically
2. **Unified Billing**: All AWS services on one bill
3. **Better Integration**: Native AWS service with CloudWatch logging
4. **Cost Tracking**: AWS Cost Explorer for detailed usage
5. **Security**: IAM policies control access, no secrets to rotate

## Architecture Changes

### Code Changes

#### 1. New Bedrock Client (`bedrock_client.py`)

Created a drop-in replacement for the Anthropic SDK that:
- Mimics the same API interface
- Uses `boto3` to call Bedrock
- Handles model ID conversion automatically
- Supports both streaming and non-streaming responses

#### 2. Updated Services

**claude_service.py**:
```python
# Before
import anthropic
client = anthropic.Anthropic(api_key=api_key)

# After
from .bedrock_client import BedrockClient
client = BedrockClient()  # No API key needed
```

**genai.py**:
```python
# Before
import anthropic
client = anthropic.Anthropic(api_key=api_key)

# After
from .bedrock_client import BedrockClient
client = BedrockClient()  # No API key needed
```

#### 3. Configuration Updates

**config.py**:
```python
USE_BEDROCK: bool = os.environ.get("USE_BEDROCK", "true")
DRAFT_MODEL_ID: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
CRITIC_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

### Infrastructure Changes

#### 1. IAM Permissions

EC2 instances now have Bedrock invoke permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-*"
  ]
}
```

#### 2. Environment Variables

**Removed**:
- `ANTHROPIC_API_KEY` (when `USE_BEDROCK=true`)

**Added**:
- `USE_BEDROCK=true` (default)

**Updated**:
- `DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0`
- `CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0`

## Model ID Mapping

| Anthropic API | AWS Bedrock | Use Case |
|--------------|-------------|----------|
| `claude-opus-4-6` | `anthropic.claude-3-opus-20240229-v1:0` | High-stakes analysis |
| `claude-sonnet-4-6` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Quality evaluation |
| `claude-haiku-4-5-20251001` | `anthropic.claude-3-5-haiku-20241022-v1:0` | Fast draft generation |

The `bedrock_client.py` automatically converts model IDs, so you can use either format.

## Migration Steps

### Step 1: Enable Bedrock Model Access

1. Go to AWS Console → Bedrock → Model access
2. Request access to:
   - Claude 3.5 Sonnet
   - Claude 3.5 Haiku
   - Claude 3 Opus (optional)
   - Amazon Titan Image Generator v2

3. Wait for approval (usually instant for Claude models)

### Step 2: Update Terraform Variables

Edit `infrastructure/environments/dev/terraform.tfvars`:

```hcl
# Enable Bedrock
use_bedrock = true

# Update model IDs to Bedrock format
draft_model_id  = "anthropic.claude-3-5-haiku-20241022-v1:0"
critic_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
vision_model_id = ""  # Optional
```

### Step 3: Apply Terraform Changes

```bash
cd infrastructure/environments/dev
terraform plan
terraform apply
```

This will:
- Update EC2 launch template with new environment variables
- Trigger instance refresh to deploy changes
- No downtime (rolling update)

### Step 4: Verify Deployment

#### Check Environment Variables

SSH into an EC2 instance:
```bash
docker exec rivet-backend env | grep -E "USE_BEDROCK|MODEL_ID"
```

Expected output:
```
USE_BEDROCK=true
DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

#### Test API Endpoint

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?Tags[?Key=='Project' && Value=='rivet']].DNSName" \
  --output text)

# Test analysis endpoint (requires valid image upload)
curl -X POST http://$ALB_DNS/api/analyze \
  -F "image=@test_image.jpg" \
  -F "category=saree"
```

#### Check CloudWatch Logs

```bash
aws logs tail /ec2/rivet-dev --follow --filter-pattern "Bedrock"
```

Look for:
```
Bedrock client initialized [region=us-east-1]
```

### Step 5: Monitor Costs

#### CloudWatch Metrics

Bedrock automatically logs:
- Model invocations
- Token usage
- Latency
- Errors

View in CloudWatch → Metrics → Bedrock

#### Cost Explorer

1. Go to AWS Cost Explorer
2. Filter by Service: "Amazon Bedrock"
3. Group by: "Usage Type"
4. View daily costs

## Rollback Plan

If you need to revert to Anthropic API:

### Option 1: Environment Variable (Quick)

```bash
# Update ASG launch template
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name rivet-dev-asg \
  --launch-template LaunchTemplateId=lt-xxx,Version='$Latest'

# Set USE_BEDROCK=false in user data
# Trigger instance refresh
```

### Option 2: Terraform (Clean)

```hcl
# terraform.tfvars
use_bedrock = false

# Revert model IDs
draft_model_id  = "claude-haiku-4-5-20251001"
critic_model_id = "claude-sonnet-4-6"
```

```bash
terraform apply
```

## Cost Comparison

### Anthropic API Pricing (as of 2024)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3.5 Haiku | $0.80 | $4.00 |
| Claude 3 Opus | $15.00 | $75.00 |

### AWS Bedrock Pricing (us-east-1)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3.5 Haiku | $0.80 | $4.00 |
| Claude 3 Opus | $15.00 | $75.00 |
| Titan Image Generator | $0.008 per image | - |

**Note**: Prices are the same, but Bedrock offers:
- Unified AWS billing
- Volume discounts (Enterprise agreements)
- Better cost tracking with AWS Cost Explorer

## Troubleshooting

### Error: "Could not connect to the endpoint URL"

**Cause**: Bedrock not available in region

**Solution**: Verify region is `us-east-1` (Bedrock is region-specific)

```python
# Check region
import os
print(os.environ.get("AWS_REGION"))
```

### Error: "AccessDeniedException"

**Cause**: IAM role missing Bedrock permissions

**Solution**: Verify IAM role has `bedrock:InvokeModel` permission

```bash
aws iam get-role-policy \
  --role-name rivet-dev-ec2-role \
  --policy-name bedrock-invoke
```

### Error: "ValidationException: The provided model identifier is invalid"

**Cause**: Model not enabled or wrong model ID

**Solution**: 
1. Check model access in Bedrock console
2. Verify model ID format: `anthropic.claude-3-5-sonnet-20241022-v2:0`

### Error: "ThrottlingException"

**Cause**: Rate limit exceeded

**Solution**: 
1. Implement exponential backoff (already in `bedrock_client.py`)
2. Request quota increase in Service Quotas console

### Performance Issues

**Symptom**: Slower response times

**Cause**: Cold start or network latency

**Solution**:
1. Check CloudWatch metrics for latency
2. Verify EC2 instances are in same region as Bedrock
3. Consider using Provisioned Throughput for consistent performance

## Best Practices

### 1. Model Selection

- **Haiku**: Fast, cheap, good for drafts and simple tasks
- **Sonnet**: Balanced, best for most use cases
- **Opus**: Expensive, use only for critical analysis

### 2. Error Handling

The `bedrock_client.py` includes:
- Automatic retries (2 attempts)
- Exponential backoff
- Timeout handling (120 seconds)

### 3. Monitoring

Set up CloudWatch alarms for:
- High latency (>5 seconds)
- Error rate (>5%)
- Token usage (cost control)

### 4. Cost Optimization

- Use Haiku for draft generation (80% cheaper than Sonnet)
- Cache responses when possible
- Implement circuit breaker to prevent runaway costs
- Set up billing alerts

## Testing

### Unit Tests

```python
# Test Bedrock client
from src.services.bedrock_client import BedrockClient

client = BedrockClient()
response = client.messages.create(
    model="anthropic.claude-3-5-haiku-20241022-v1:0",
    max_tokens=100,
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.content[0].text)
```

### Integration Tests

```bash
# Run existing tests (should pass with Bedrock)
cd application
pytest tests/test_genai.py -v
```

## Support

### AWS Support

- Bedrock documentation: https://docs.aws.amazon.com/bedrock/
- Service quotas: https://console.aws.amazon.com/servicequotas/
- Support cases: https://console.aws.amazon.com/support/

### Internal Support

- Check CloudWatch logs: `/ec2/rivet-dev`
- Review Terraform state: `terraform show`
- Contact DevOps team for infrastructure issues

## Next Steps

1. Monitor costs for first week
2. Optimize model selection based on usage patterns
3. Set up CloudWatch dashboards for Bedrock metrics
4. Consider Provisioned Throughput for production
5. Implement caching layer for repeated queries
