# Bedrock Model Access Required

## Current Issue

The application is failing because AWS Bedrock requires you to request access to Anthropic Claude models before you can use them. You're seeing this error:

```
Model use case details have not been submitted for this account. 
Fill out the Anthropic use case details form before using the model.
```

## Solution: Request Model Access

You need to request access to Claude models in the AWS Bedrock console:

### Steps:

1. **Go to AWS Bedrock Console**:
   - Navigate to: https://console.aws.amazon.com/bedrock/
   - Make sure you're in the `us-east-1` region

2. **Request Model Access**:
   - Click on "Model access" in the left sidebar
   - Click "Manage model access" or "Request model access"
   - Find "Anthropic" in the list
   - Check the box next to "Claude 3 Haiku"
   - Fill out the use case form (describe your fashion design analysis application)
   - Click "Request model access"

3. **Wait for Approval**:
   - Access is usually granted within a few minutes
   - You'll receive an email confirmation
   - The status will change from "Pending" to "Access granted"

4. **Test the Application**:
   - Once access is granted, the application should work immediately
   - No code changes or redeployment needed
   - Try the analysis endpoint again

## Alternative: Use Anthropic API Directly

If you don't want to wait for Bedrock model access, you can use the Anthropic API directly:

1. **Get an Anthropic API Key**:
   - Go to: https://console.anthropic.com/
   - Create an account and get an API key

2. **Update the Secret in AWS**:
   ```bash
   aws secretsmanager update-secret \
     --secret-id rivet-prod/anthropic-api-key \
     --secret-string "your-actual-anthropic-api-key-here" \
     --region us-east-1
   ```

3. **Update Environment Variable**:
   - The infrastructure is already configured to support both Bedrock and Anthropic API
   - The application will automatically use the Anthropic API if USE_BEDROCK=false
   - Currently USE_BEDROCK=true, so it's trying to use Bedrock

## Recommended Approach

**Use Bedrock** (recommended for production):
- No additional API costs beyond AWS
- Better integration with AWS services
- Just need to request model access once

**Use Anthropic API** (quick alternative):
- Works immediately with an API key
- Separate billing from AWS
- Good for testing/development

## Current Configuration

- **USE_BEDROCK**: true
- **Model**: Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0)
- **Region**: us-east-1
- **Status**: Waiting for model access approval

## Next Steps

1. Request Claude 3 Haiku access in AWS Bedrock console
2. Wait for approval (usually < 15 minutes)
3. Test the application - it should work automatically

OR

1. Get an Anthropic API key
2. Update the secret in AWS Secrets Manager
3. Redeploy with USE_BEDROCK=false
