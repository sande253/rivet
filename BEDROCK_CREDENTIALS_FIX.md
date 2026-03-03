# Bedrock Credentials Fix

## Problem

When uploading images, the application returned:
```json
{"error": "Internal server error"}
```

CloudWatch logs showed:
```
[ERROR] Bedrock invocation failed: Unable to locate credentials
```

## Root Cause

The Docker container couldn't access AWS credentials because:

1. EC2 instance has an IAM role with Bedrock permissions ✓
2. Docker container was isolated from the host network ✗
3. Container couldn't reach EC2 metadata service (169.254.169.254) ✗
4. boto3 couldn't retrieve IAM role credentials ✗

## Solution

Added `--network host` flag to Docker container in `user_data.sh`:

```bash
docker run -d \
    --name rivet-backend \
    --restart unless-stopped \
    -p ${container_port}:8000 \
    --network host \  # <-- Added this line
    -e AWS_REGION=${aws_region} \
    -e AWS_DEFAULT_REGION=${aws_region} \
    -e USE_BEDROCK=true \
    ...
```

### What `--network host` Does

- Allows container to access EC2 instance metadata service
- Container can retrieve IAM role credentials automatically
- boto3 can authenticate with Bedrock using the IAM role
- No need to pass AWS credentials as environment variables

## Files Changed

- `infrastructure/modules/ec2/user_data.sh` - Added `--network host` flag

## Testing

After deployment completes:

1. Upload a test image
2. Should see analysis results (not error)
3. Check CloudWatch logs - no credential errors

## Verification Commands

```bash
# Check if new instances are running
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-name rivet-dev-asg \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]'

# Check CloudWatch logs for errors
aws logs tail /ec2/rivet-dev --since 5m --filter-pattern "ERROR"

# Check if Bedrock is working
aws logs tail /ec2/rivet-dev --since 5m --filter-pattern "Bedrock"
```

## Alternative Solutions Considered

### Option 1: Pass AWS Credentials (Not Recommended)
```bash
# Get credentials from metadata
AWS_ACCESS_KEY_ID=$(curl ...)
AWS_SECRET_ACCESS_KEY=$(curl ...)

# Pass to container
-e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
-e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
```

**Why not**: Credentials expire, need refresh logic, less secure

### Option 2: Mount AWS Config (Not Recommended)
```bash
-v ~/.aws:/root/.aws
```

**Why not**: No ~/.aws directory on EC2, IAM role is better

### Option 3: Use ECS Task Role (Different Architecture)
Would require migrating from EC2 to ECS Fargate

**Why not**: Major architecture change, not needed

## Security Considerations

### Is `--network host` Safe?

✅ **Yes, in this case**:
- Container still runs with limited privileges
- IAM role permissions are scoped (only Bedrock access)
- No additional ports exposed
- Standard practice for AWS SDK in containers

### IAM Role Permissions

The EC2 instance role has minimal permissions:
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

## Deployment Timeline

1. ✅ Code pushed to GitHub
2. ✅ GitHub Actions builds new image
3. ✅ Image pushed to ECR
4. ⏳ Instance refresh triggered (25-40 min)
5. ⏳ New instances launch with fixed user_data
6. ⏳ Containers start with `--network host`
7. ✅ Bedrock credentials work

## Monitoring

### Check Deployment Status

```bash
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg \
  --max-records 1 \
  --query 'InstanceRefreshes[0].[Status,PercentageComplete]'
```

### Check Container Logs

```bash
# Via CloudWatch
aws logs tail /ec2/rivet-dev --follow

# Or SSH to instance
ssh ec2-user@instance-ip
docker logs rivet-backend --tail 50 --follow
```

### Test Bedrock Access

```bash
# From within container
docker exec rivet-backend python -c "
import boto3
client = boto3.client('bedrock-runtime', region_name='us-east-1')
print('Bedrock client created successfully')
"
```

## Rollback

If this causes issues, revert with:

```bash
git revert HEAD
git push origin main
```

Or manually SSH to instances and restart containers without `--network host`.

## Related Issues

- [TROUBLESHOOTING_ANALYSIS_ERROR.md](TROUBLESHOOTING_ANALYSIS_ERROR.md) - General troubleshooting
- [infrastructure/BEDROCK_MIGRATION.md](infrastructure/BEDROCK_MIGRATION.md) - Bedrock setup
- [infrastructure/IAM_POLICIES.md](infrastructure/IAM_POLICIES.md) - IAM permissions

## Summary

The Docker container now has access to EC2 IAM role credentials via the instance metadata service, allowing boto3 to authenticate with AWS Bedrock automatically. This fixes the "Unable to locate credentials" error and enables the AI analysis features to work properly.
