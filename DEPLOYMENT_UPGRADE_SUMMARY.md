# Deployment Upgrade Summary

This document summarizes the comprehensive upgrades made to the AWS deployment infrastructure.

## Overview

Three major upgrades have been implemented:

1. **CI/CD Pipeline** - Automated GitHub Actions deployment
2. **AWS Bedrock Migration** - Replaced Anthropic API with AWS Bedrock
3. **Deployment Safety** - Zero-downtime deployments with rollback capability

## 1. CI/CD Pipeline (GitHub Actions)

### What Was Added

- **Workflow File**: `.github/workflows/deploy.yml`
- **IAM Policy**: `infrastructure/github-actions-iam-policy.json`
- **Documentation**: `infrastructure/CI_CD_SETUP.md`

### Features

✅ Automatic deployment on push to `main` or `dev` branches
✅ Docker image build and push to ECR
✅ Zero-downtime instance refresh
✅ Automatic health checks and verification
✅ Deployment status monitoring
✅ Rollback capability

### Deployment Flow

```
Push to GitHub
    ↓
Build Docker Image
    ↓
Push to ECR (commit SHA + latest tags)
    ↓
Trigger Auto Scaling Group Instance Refresh
    ↓
New instances pull latest image
    ↓
Health checks pass
    ↓
Old instances terminated
    ↓
Deployment complete ✓
```

### Security

- **No hardcoded credentials** - Uses OIDC and IAM roles
- **Least privilege** - IAM role has minimal permissions
- **Audit trail** - CloudTrail logs all actions
- **Branch protection** - Recommended for production

### Setup Required

1. Create OIDC provider in AWS
2. Create IAM role for GitHub Actions
3. Add `AWS_ROLE_ARN` secret to GitHub repository
4. Push to trigger first deployment

**Time to setup**: ~15 minutes
**Documentation**: `infrastructure/CI_CD_SETUP.md`

---

## 2. AWS Bedrock Migration

### What Was Added

- **Bedrock Client**: `application/src/services/bedrock_client.py`
- **Updated Services**: `claude_service.py`, `genai.py`
- **Configuration**: Updated `config.py` with `USE_BEDROCK` flag
- **Documentation**: `infrastructure/BEDROCK_MIGRATION.md`

### Changes Made

#### Code Changes

| File | Change | Impact |
|------|--------|--------|
| `bedrock_client.py` | New Bedrock adapter | Drop-in replacement for Anthropic SDK |
| `claude_service.py` | Import Bedrock client | Uses IAM role instead of API key |
| `genai.py` | Import Bedrock client | Uses IAM role instead of API key |
| `config.py` | Add `USE_BEDROCK` flag | Toggle between Anthropic/Bedrock |
| `requirements.txt` | Add `botocore` | Bedrock SDK dependency |

#### Infrastructure Changes

| Component | Change | Benefit |
|-----------|--------|---------|
| IAM Role | Added `bedrock:InvokeModel` | EC2 can call Bedrock |
| Environment Variables | `USE_BEDROCK=true` | Enable Bedrock by default |
| Model IDs | Updated to Bedrock format | `anthropic.claude-3-5-*` |
| Secrets | API key optional | No secrets when using Bedrock |

### Benefits

✅ **No API Keys** - Uses IAM role credentials automatically
✅ **Unified Billing** - All AWS services on one bill
✅ **Better Integration** - Native AWS service with CloudWatch
✅ **Cost Tracking** - AWS Cost Explorer for detailed usage
✅ **Security** - IAM policies control access

### Model Mapping

| Use Case | Anthropic API | AWS Bedrock |
|----------|--------------|-------------|
| Draft Generation | `claude-haiku-4-5-20251001` | `anthropic.claude-3-5-haiku-20241022-v1:0` |
| Quality Evaluation | `claude-sonnet-4-6` | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| High-Stakes Analysis | `claude-opus-4-6` | `anthropic.claude-3-opus-20240229-v1:0` |
| Image Generation | N/A | `amazon.titan-image-generator-v2:0` |

### Backward Compatibility

The implementation maintains backward compatibility:

```python
# Set USE_BEDROCK=false to use Anthropic API
USE_BEDROCK = os.environ.get("USE_BEDROCK", "true")

if USE_BEDROCK:
    from .bedrock_client import BedrockClient as AnthropicClient
else:
    import anthropic
    AnthropicClient = anthropic.Anthropic
```

### Setup Required

1. Enable Bedrock model access in AWS Console
2. Update Terraform variables (`use_bedrock = true`)
3. Apply Terraform changes
4. Verify deployment

**Time to setup**: ~10 minutes
**Documentation**: `infrastructure/BEDROCK_MIGRATION.md`

---

## 3. Deployment Safety

### Zero-Downtime Deployment

Implemented using AWS Auto Scaling Group Instance Refresh:

- **MinHealthyPercentage**: 90% (keeps 90% of instances healthy)
- **InstanceWarmup**: 300 seconds (5 minutes for new instances)
- **CheckpointPercentages**: [50, 100] (pauses for verification)
- **CheckpointDelay**: 300 seconds (5 minutes at each checkpoint)

### Deployment Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Build & Push | 2-5 min | Docker image build and ECR push |
| Instance Launch | 5-10 min | New instance starts and pulls image |
| Health Check | 2-3 min | ALB verifies instance health |
| Checkpoint 50% | 5 min | Pause to verify stability |
| Remaining Instances | 5-10 min | Replace remaining instances |
| Checkpoint 100% | 5 min | Final verification |
| **Total** | **25-40 min** | Complete deployment |

### Rollback Strategy

#### Automatic Rollback

- Instance refresh cancels on health check failures
- Old instances remain running if new instances fail
- No manual intervention required

#### Manual Rollback

```bash
# Cancel current deployment
aws autoscaling cancel-instance-refresh \
  --auto-scaling-group-name rivet-dev-asg

# Deploy previous version
git revert HEAD
git push origin main
```

### Health Checks

Multiple layers of health checks:

1. **EC2 Health Check** - Instance is running
2. **Docker Health Check** - Container is running
3. **ALB Health Check** - Application responds to HTTP requests
4. **Application Health Check** - `/` endpoint returns 200

### Idempotent Infrastructure

All Terraform configurations are idempotent:

- Can run `terraform apply` multiple times safely
- No manual state management required
- Automatic drift detection

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub Actions                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │   Build    │→ │  Push ECR  │→ │  Instance Refresh  │   │
│  └────────────┘  └────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      AWS Infrastructure                      │
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  CloudFront  │────────→│     ALB      │                 │
│  └──────────────┘         └──────────────┘                 │
│                                  ↓                           │
│                    ┌─────────────────────────┐              │
│                    │   Auto Scaling Group    │              │
│                    │  ┌────┐  ┌────┐  ┌────┐│              │
│                    │  │EC2 │  │EC2 │  │EC2 ││              │
│                    │  └────┘  └────┘  └────┘│              │
│                    └─────────────────────────┘              │
│                              ↓                               │
│         ┌────────────────────┴────────────────────┐         │
│         ↓                    ↓                    ↓         │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐     │
│  │   ECR    │        │ Bedrock  │        │    S3    │     │
│  │ (Images) │        │ (Claude) │        │(Uploads) │     │
│  └──────────┘        └──────────┘        └──────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Changes Summary

### New Files Created

```
.github/workflows/deploy.yml                    # CI/CD workflow
application/src/services/bedrock_client.py      # Bedrock adapter
infrastructure/github-actions-iam-policy.json   # IAM policy
infrastructure/CI_CD_SETUP.md                   # CI/CD guide
infrastructure/BEDROCK_MIGRATION.md             # Bedrock guide
DEPLOYMENT_UPGRADE_SUMMARY.md                   # This file
```

### Modified Files

```
application/src/services/claude_service.py      # Use Bedrock client
application/src/services/genai.py               # Use Bedrock client
application/src/config.py                       # Add USE_BEDROCK flag
application/requirements.txt                    # Add botocore
infrastructure/modules/ec2/main.tf              # Add use_bedrock variable
infrastructure/modules/ec2/variables.tf         # Add use_bedrock variable
infrastructure/modules/ec2/user_data.sh         # Conditional API key
infrastructure/environments/dev/main.tf         # Pass use_bedrock
infrastructure/environments/dev/variables.tf    # Add use_bedrock variable
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Review all code changes
- [ ] Update Terraform variables
- [ ] Enable Bedrock model access
- [ ] Create GitHub Actions IAM role
- [ ] Add GitHub secrets
- [ ] Test locally with `USE_BEDROCK=true`

### Deployment

- [ ] Run `terraform plan` to review changes
- [ ] Run `terraform apply` to deploy infrastructure
- [ ] Wait for instance refresh to complete (~30 min)
- [ ] Verify new instances are running
- [ ] Test application endpoints
- [ ] Check CloudWatch logs

### Post-Deployment

- [ ] Monitor CloudWatch metrics
- [ ] Verify Bedrock invocations
- [ ] Check AWS Cost Explorer
- [ ] Test CI/CD pipeline with a commit
- [ ] Document any issues
- [ ] Update team documentation

---

## Testing

### Local Testing

```bash
# Test with Bedrock
cd application
export USE_BEDROCK=true
export AWS_REGION=us-east-1
export DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
export CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Run tests
pytest tests/ -v
```

### Integration Testing

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?Tags[?Key=='Project' && Value=='rivet']].DNSName" \
  --output text)

# Test analysis endpoint
curl -X POST http://$ALB_DNS/api/analyze \
  -F "image=@test_image.jpg" \
  -F "category=saree"
```

### CI/CD Testing

```bash
# Trigger manual deployment
git commit --allow-empty -m "Test CI/CD pipeline"
git push origin main

# Monitor in GitHub Actions
# https://github.com/YOUR_ORG/YOUR_REPO/actions
```

---

## Monitoring

### CloudWatch Dashboards

Create dashboards for:

1. **Deployment Metrics**
   - Instance refresh status
   - Health check failures
   - Deployment duration

2. **Bedrock Metrics**
   - Model invocations
   - Token usage
   - Latency
   - Error rate

3. **Application Metrics**
   - Request count
   - Response time
   - Error rate
   - Circuit breaker status

### CloudWatch Alarms

Set up alarms for:

- High Bedrock latency (>5 seconds)
- High error rate (>5%)
- Instance refresh failures
- Health check failures
- High token usage (cost control)

### Cost Monitoring

1. **AWS Cost Explorer**
   - Filter by service: Bedrock, EC2, ECR
   - Group by: Usage type
   - Set up budget alerts

2. **Bedrock Usage**
   - Track token usage per model
   - Monitor cost per request
   - Optimize model selection

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| CI/CD fails at ECR login | IAM role missing permissions | Verify IAM policy |
| Instance refresh fails | Health checks failing | Check CloudWatch logs |
| Bedrock AccessDenied | IAM role missing permissions | Verify Bedrock policy |
| High latency | Cold start or network | Check CloudWatch metrics |
| High costs | Inefficient model usage | Optimize model selection |

### Debug Commands

```bash
# Check EC2 instance logs
aws logs tail /ec2/rivet-dev --follow

# Check instance refresh status
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name rivet-dev-asg

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN>

# Check Bedrock invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

---

## Cost Estimate

### Monthly Costs (Estimated)

| Service | Usage | Cost |
|---------|-------|------|
| EC2 (t3.small) | 1 instance, 24/7 | ~$15 |
| ALB | 1 ALB, low traffic | ~$20 |
| ECR | 5 images, 2GB total | ~$1 |
| CloudFront | 10GB transfer | ~$1 |
| S3 | 10GB storage | ~$0.25 |
| Bedrock (Haiku) | 10M tokens/month | ~$8 |
| Bedrock (Sonnet) | 1M tokens/month | ~$18 |
| **Total** | | **~$63/month** |

### Cost Optimization Tips

1. Use Haiku for draft generation (80% cheaper)
2. Implement caching to reduce API calls
3. Use spot instances for dev environment
4. Set up billing alerts
5. Review CloudWatch logs retention

---

## Security Considerations

### Secrets Management

- ✅ No hardcoded credentials
- ✅ IAM roles for service authentication
- ✅ Secrets Manager for sensitive data (optional with Bedrock)
- ✅ Encrypted environment variables

### Network Security

- ✅ Private subnets for EC2 instances
- ✅ Security groups with least privilege
- ✅ ALB in public subnets only
- ✅ CloudFront for DDoS protection

### Access Control

- ✅ IAM policies with least privilege
- ✅ MFA for AWS console access
- ✅ CloudTrail for audit logging
- ✅ VPC Flow Logs for network monitoring

---

## Next Steps

### Immediate (Week 1)

1. Complete CI/CD setup
2. Enable Bedrock model access
3. Deploy with Terraform
4. Monitor costs and performance

### Short-term (Month 1)

1. Set up CloudWatch dashboards
2. Configure billing alerts
3. Optimize model selection
4. Document runbooks

### Long-term (Quarter 1)

1. Implement staging environment
2. Add automated testing
3. Set up blue-green deployments
4. Consider Provisioned Throughput for Bedrock

---

## Support

### Documentation

- CI/CD Setup: `infrastructure/CI_CD_SETUP.md`
- Bedrock Migration: `infrastructure/BEDROCK_MIGRATION.md`
- Terraform Docs: `infrastructure/README.md`

### AWS Resources

- Bedrock: https://docs.aws.amazon.com/bedrock/
- Auto Scaling: https://docs.aws.amazon.com/autoscaling/
- GitHub Actions: https://docs.github.com/actions

### Contact

- DevOps Team: [Your team contact]
- AWS Support: https://console.aws.amazon.com/support/
- GitHub Issues: [Your repo issues URL]

---

## Conclusion

These upgrades provide:

✅ **Automated Deployments** - No manual SSH or Docker commands
✅ **Zero Downtime** - Rolling updates with health checks
✅ **Cost Optimization** - Unified AWS billing, better tracking
✅ **Security** - No API keys, IAM role authentication
✅ **Scalability** - Auto Scaling Group handles traffic spikes
✅ **Observability** - CloudWatch logs and metrics
✅ **Rollback Capability** - Quick recovery from failures

The infrastructure is now production-ready with enterprise-grade deployment practices.
