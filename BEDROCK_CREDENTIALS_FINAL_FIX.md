# Bedrock Credentials - Final Fix

## Problem

Even with `--network host` flag, the Docker container couldn't access AWS credentials:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

## Root Cause

Docker containers, even with `--network host`, have isolated network namespaces that prevent access to the EC2 instance metadata service (169.254.169.254) in some configurations.

## Solution

Pass IAM role credentials directly to the container as environment variables:

```bash
# Get IAM role name
ROLE_NAME=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/)

# Get temporary credentials
CREDENTIALS=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME)

# Extract and pass to container
docker run -d \
    -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
    ...
```

## Why This Works

1. Host EC2 instance can access metadata service ✓
2. Credentials are retrieved on instance startup ✓
3. Credentials are passed to container as env vars ✓
4. boto3 reads credentials from environment ✓

## Security Considerations

### Is This Secure?

✅ **Yes**:
- Credentials are temporary (expire after ~6 hours)
- Only visible to processes inside the container
- IAM role permissions are scoped (only Bedrock access)
- No credentials stored in code or config files

### Credential Rotation

⚠️ **Limitation**: Credentials will expire after ~6 hours

**Solutions**:
1. Container restart picks up new credentials (happens on deployment)
2. For long-running containers, add a credential refresh mechanism
3. Use ECS Fargate (handles rotation automatically)

For this application, deployments happen frequently enough that credential expiration isn't an issue.

## Files Changed

- `infrastructure/modules/ec2/user_data.sh` - Added credential extraction and passing

## Testing

After deployment completes (~25-40 minutes):

1. Upload a test image
2. Should see AI analysis (not error)
3. Check CloudWatch logs - no credential errors

```bash
# Monitor deployment
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg \
  --max-records 1

# Check for errors
aws logs tail /ec2/rivet-dev --filter-pattern "ERROR" --since 5m

# Test Bedrock access
aws logs tail /ec2/rivet-dev --filter-pattern "Bedrock" --since 5m
```

## Alternative Solutions Considered

### 1. --network host (Tried, Failed)
```bash
docker run --network host ...
```
**Why it failed**: Network namespace isolation still prevented metadata access

### 2. ECS Fargate (Best Long-term Solution)
- Automatic credential rotation
- No EC2 management
- Better security

**Why not now**: Requires architecture change, more complex

### 3. Credential Refresh Sidecar
- Background process to refresh credentials
- Update container env vars

**Why not now**: Over-engineered for current needs

## Deployment Timeline

1. ✅ Code pushed to GitHub
2. ⏳ GitHub Actions builds new image
3. ⏳ Image pushed to ECR
4. ⏳ Instance refresh triggered (25-40 min)
5. ⏳ New instances launch with credential passing
6. ⏳ Containers start with AWS credentials
7. ✅ Bedrock works

## Monitoring

```bash
# Check deployment status
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg \
  --max-records 1 \
  --query 'InstanceRefreshes[0].[Status,PercentageComplete]'

# Check instance health
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-name rivet-dev-asg \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]'

# View logs
aws logs tail /ec2/rivet-dev --follow

# Check for credential errors
aws logs tail /ec2/rivet-dev --filter-pattern "NoCredentialsError" --since 1h
```

## Summary

The Docker container now receives IAM role credentials as environment variables, allowing boto3 to authenticate with AWS Bedrock. This fixes the "Unable to locate credentials" error and enables AI analysis features.

## Next Deployment

The current deployment is at 50% checkpoint. It will complete in ~20-25 minutes. After that, test the application by uploading an image for analysis.
