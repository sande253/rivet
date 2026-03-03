# Visual Deployment Guide

A visual walkthrough of the deployment upgrade implementation.

## 🎯 Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT UPGRADES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CI/CD Pipeline        →  Automated deployments             │
│  2. AWS Bedrock          →  No API keys needed                 │
│  3. Zero Downtime        →  Rolling updates                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Architecture Evolution

### Before: Manual Deployment
```
┌──────────┐
│Developer │
└────┬─────┘
     │ SSH
     ↓
┌─────────────┐      ┌──────────────┐
│   EC2       │─────→│ Anthropic API│
│  Instance   │      │  (API Key)   │
└──────┬──────┘      └──────────────┘
       │
       ↓
   ┌───────┐
   │   S3  │
   └───────┘

Issues:
❌ Manual SSH required
❌ Downtime during updates
❌ API keys to manage
❌ No automation
```

### After: Automated Deployment
```
┌──────────┐
│Developer │
└────┬─────┘
     │ git push
     ↓
┌─────────────────┐
│ GitHub Actions  │
│    (CI/CD)      │
└────┬────────────┘
     │ Build & Deploy
     ↓
┌─────────────────┐
│      ECR        │
│ (Docker Images) │
└────┬────────────┘
     │ Pull
     ↓
┌──────────────────────────────────────┐
│     Auto Scaling Group               │
│  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │  EC2   │  │  EC2   │  │  EC2   │ │
│  └───┬────┘  └───┬────┘  └───┬────┘ │
└──────┼───────────┼───────────┼───────┘
       │           │           │
       └───────────┴───────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ↓                       ↓
┌──────────────┐      ┌──────────────┐
│   Bedrock    │      │      S3      │
│ (IAM Role)   │      │  (Uploads)   │
└──────────────┘      └──────────────┘

Benefits:
✅ Automated deployments
✅ Zero downtime
✅ No API keys
✅ Auto scaling
```

## 🔄 Deployment Flow

### Step-by-Step Process

```
1. Developer Commits Code
   ┌──────────────┐
   │ git push     │
   │ origin main  │
   └──────┬───────┘
          │
          ↓
2. GitHub Actions Triggered
   ┌──────────────────────┐
   │ Workflow starts      │
   │ - Checkout code      │
   │ - Configure AWS      │
   └──────┬───────────────┘
          │
          ↓
3. Build Docker Image
   ┌──────────────────────┐
   │ docker build         │
   │ Tag: commit-sha      │
   │ Tag: latest          │
   └──────┬───────────────┘
          │
          ↓
4. Push to ECR
   ┌──────────────────────┐
   │ docker push          │
   │ Image stored in ECR  │
   └──────┬───────────────┘
          │
          ↓
5. Trigger Instance Refresh
   ┌──────────────────────┐
   │ ASG starts refresh   │
   │ MinHealthy: 90%      │
   └──────┬───────────────┘
          │
          ↓
6. Launch New Instances
   ┌──────────────────────┐
   │ New EC2 starts       │
   │ Pulls latest image   │
   │ Runs container       │
   └──────┬───────────────┘
          │
          ↓
7. Health Checks
   ┌──────────────────────┐
   │ ALB checks health    │
   │ Wait for healthy     │
   └──────┬───────────────┘
          │
          ↓
8. Terminate Old Instances
   ┌──────────────────────┐
   │ Old instances stop   │
   │ Traffic shifted      │
   └──────┬───────────────┘
          │
          ↓
9. Deployment Complete ✅
   ┌──────────────────────┐
   │ All instances new    │
   │ Application updated  │
   └──────────────────────┘
```

## 🔐 Security Architecture

### IAM Roles and Permissions

```
┌─────────────────────────────────────────────────────────────┐
│                     IAM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────┘

GitHub Actions Role
┌──────────────────────┐
│ GitHubActionsRole    │
│                      │
│ Permissions:         │
│ ✓ ECR Push           │
│ ✓ ASG Refresh        │
│ ✓ ALB Describe       │
└──────────────────────┘
         │
         │ OIDC Trust
         ↓
┌──────────────────────┐
│ GitHub Workflow      │
│ .github/workflows/   │
│ deploy.yml           │
└──────────────────────┘

EC2 Instance Role
┌──────────────────────┐
│ EC2InstanceRole      │
│                      │
│ Permissions:         │
│ ✓ Bedrock Invoke     │
│ ✓ S3 Read/Write      │
│ ✓ ECR Pull           │
│ ✓ CloudWatch Logs    │
│ ✓ Secrets Manager    │
└──────────────────────┘
         │
         │ Attached to
         ↓
┌──────────────────────┐
│ EC2 Instances        │
│ (Auto Scaling Group) │
└──────────────────────┘
```

## 🔄 Zero-Downtime Deployment

### Rolling Update Process

```
Time: T+0 (Start)
┌─────────────────────────────────────────┐
│ Current State: 2 instances running      │
│ ┌────────┐  ┌────────┐                 │
│ │ EC2-1  │  │ EC2-2  │                 │
│ │ v1.0   │  │ v1.0   │                 │
│ └────────┘  └────────┘                 │
│ Traffic: 50%   50%                      │
└─────────────────────────────────────────┘

Time: T+5min (First instance)
┌─────────────────────────────────────────┐
│ Launch new instance with v2.0           │
│ ┌────────┐  ┌────────┐  ┌────────┐    │
│ │ EC2-1  │  │ EC2-2  │  │ EC2-3  │    │
│ │ v1.0   │  │ v1.0   │  │ v2.0   │    │
│ └────────┘  └────────┘  └────────┘    │
│ Traffic: 40%   40%       20%           │
└─────────────────────────────────────────┘

Time: T+10min (Health check passed)
┌─────────────────────────────────────────┐
│ Terminate EC2-1, keep EC2-2 & EC2-3     │
│              ┌────────┐  ┌────────┐    │
│              │ EC2-2  │  │ EC2-3  │    │
│              │ v1.0   │  │ v2.0   │    │
│              └────────┘  └────────┘    │
│ Traffic:        50%       50%           │
└─────────────────────────────────────────┘

Time: T+15min (Checkpoint 50%)
┌─────────────────────────────────────────┐
│ Pause for 5 minutes to verify stability│
│              ┌────────┐  ┌────────┐    │
│              │ EC2-2  │  │ EC2-3  │    │
│              │ v1.0   │  │ v2.0   │    │
│              └────────┘  └────────┘    │
│ Status: Monitoring...                   │
└─────────────────────────────────────────┘

Time: T+20min (Second instance)
┌─────────────────────────────────────────┐
│ Launch another new instance             │
│              ┌────────┐  ┌────────┐    │
│              │ EC2-3  │  │ EC2-4  │    │
│              │ v2.0   │  │ v2.0   │    │
│              └────────┘  └────────┘    │
│ Traffic:        50%       50%           │
└─────────────────────────────────────────┘

Time: T+30min (Complete)
┌─────────────────────────────────────────┐
│ All instances running v2.0              │
│              ┌────────┐  ┌────────┐    │
│              │ EC2-3  │  │ EC2-4  │    │
│              │ v2.0   │  │ v2.0   │    │
│              └────────┘  └────────┘    │
│ Status: ✅ Deployment Complete          │
└─────────────────────────────────────────┘

Key Points:
✅ Always maintain 90% capacity
✅ Health checks at each step
✅ Automatic rollback on failure
✅ No user-facing downtime
```

## 🤖 Bedrock Integration

### API Call Flow

```
Before (Anthropic API)
┌──────────────┐
│ Application  │
└──────┬───────┘
       │ HTTP Request
       │ + API Key
       ↓
┌──────────────┐
│ Anthropic    │
│ API          │
└──────────────┘

Issues:
❌ API key management
❌ Separate billing
❌ Manual rotation

After (AWS Bedrock)
┌──────────────┐
│ Application  │
└──────┬───────┘
       │ boto3 call
       │ + IAM Role
       ↓
┌──────────────┐
│ AWS Bedrock  │
│ Runtime      │
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Claude Model │
│ (Sonnet/     │
│  Haiku)      │
└──────────────┘

Benefits:
✅ No API keys
✅ Unified billing
✅ Auto credentials
```

### Model Selection

```
┌─────────────────────────────────────────────────────┐
│              MODEL SELECTION FLOW                   │
└─────────────────────────────────────────────────────┘

User Request
     │
     ↓
┌─────────────────┐
│ Draft Tips      │ → Use Haiku (Fast & Cheap)
│ Generation      │   $0.80 per 1M tokens
└─────────────────┘
     │
     ↓
┌─────────────────┐
│ Quality         │ → Use Sonnet (Balanced)
│ Evaluation      │   $3.00 per 1M tokens
└─────────────────┘
     │
     ↓
┌─────────────────┐
│ Final Tips      │ → Return to User
│ (Approved)      │
└─────────────────┘

Cost Optimization:
- Haiku for drafts: 80% cheaper
- Sonnet for quality: Better accuracy
- Total cost: ~$10-20/month for typical usage
```

## 📊 Monitoring Dashboard

### CloudWatch Metrics Layout

```
┌─────────────────────────────────────────────────────────────┐
│                  RIVET MONITORING DASHBOARD                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Deployment Metrics                                         │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Instance Refresh │  │ Health Checks    │               │
│  │ Status: Success  │  │ Pass Rate: 100%  │               │
│  │ Duration: 28min  │  │ Failed: 0        │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  Application Metrics                                        │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Request Count    │  │ Response Time    │               │
│  │ 1,234 req/hour   │  │ Avg: 250ms       │               │
│  │ ▁▂▃▅▇▅▃▂▁       │  │ P95: 500ms       │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  Bedrock Metrics                                            │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Invocations      │  │ Token Usage      │               │
│  │ 456 calls/hour   │  │ 1.2M tokens/day  │               │
│  │ Haiku: 80%       │  │ Cost: $2.50/day  │               │
│  │ Sonnet: 20%      │  │ ▁▂▃▅▇▅▃▂▁       │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  Cost Metrics                                               │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Daily Cost       │  │ Monthly Forecast │               │
│  │ $2.10            │  │ $63.00           │               │
│  │ ▁▂▃▅▇▅▃▂▁       │  │ On budget ✅     │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 💰 Cost Breakdown

### Monthly Cost Visualization

```
Development Environment (~$63/month)
┌─────────────────────────────────────────────┐
│ EC2 (t3.small)      ████████████  $15  24% │
│ ALB                 █████████████ $20  32% │
│ Bedrock (Haiku)     ████          $8   13% │
│ Bedrock (Sonnet)    █████████     $18  29% │
│ ECR                 █             $1    2% │
│ CloudFront          █             $1    2% │
│ S3                  █             $0.25 0% │
└─────────────────────────────────────────────┘
Total: $63.25/month

Production Environment (~$321/month)
┌─────────────────────────────────────────────┐
│ EC2 (t3.medium x2)  ███████████   $60  19% │
│ Bedrock (Sonnet)    ████████████████ $180 56%│
│ Bedrock (Haiku)     ██████        $40  12% │
│ ALB                 █████         $30   9% │
│ CloudFront          ███           $8    2% │
│ ECR                 █             $2    1% │
│ S3                  █             $1.25 0% │
└─────────────────────────────────────────────┘
Total: $321.25/month
```

## 🎯 Implementation Timeline

### 4-Week Rollout Plan

```
Week 1: Setup & Deployment
┌─────────────────────────────────────────────┐
│ Mon  │ Enable Bedrock models               │
│ Tue  │ Configure Terraform                 │
│ Wed  │ Deploy infrastructure               │
│ Thu  │ Set up CI/CD                        │
│ Fri  │ Testing & verification              │
└─────────────────────────────────────────────┘
Time: 5-10 hours

Week 2: Monitoring
┌─────────────────────────────────────────────┐
│ Mon  │ Create CloudWatch dashboards        │
│ Tue  │ Configure alarms                    │
│ Wed  │ Set up cost monitoring              │
│ Thu  │ Document procedures                 │
│ Fri  │ Review & optimize                   │
└─────────────────────────────────────────────┘
Time: 2-4 hours

Week 3: Training
┌─────────────────────────────────────────────┐
│ Mon  │ Train team on CI/CD                 │
│ Tue  │ Train team on monitoring            │
│ Wed  │ Train team on troubleshooting       │
│ Thu  │ Document runbooks                   │
│ Fri  │ Q&A session                         │
└─────────────────────────────────────────────┘
Time: 2-4 hours

Week 4: Optimization
┌─────────────────────────────────────────────┐
│ Mon  │ Review metrics                      │
│ Tue  │ Optimize costs                      │
│ Wed  │ Fine-tune alarms                    │
│ Thu  │ Update documentation                │
│ Fri  │ Retrospective                       │
└─────────────────────────────────────────────┘
Time: 2-4 hours

Total: 11-22 hours over 4 weeks
```

## ✅ Success Checklist

### Visual Progress Tracker

```
Pre-Deployment
[ ] AWS CLI configured
[ ] Terraform installed
[ ] GitHub access
[ ] Bedrock models enabled

Infrastructure
[ ] Terraform init
[ ] Terraform plan reviewed
[ ] Terraform apply successful
[ ] Outputs verified

CI/CD Setup
[ ] OIDC provider created
[ ] IAM role created
[ ] GitHub secret added
[ ] Workflow file verified

Deployment
[ ] Docker image built
[ ] Image pushed to ECR
[ ] Instance refresh triggered
[ ] Deployment completed

Verification
[ ] Application responds
[ ] Logs show Bedrock init
[ ] GitHub Actions works
[ ] Metrics in CloudWatch

Monitoring
[ ] Dashboards created
[ ] Alarms configured
[ ] Cost tracking set up
[ ] Team trained

Progress: [████████░░] 80%
```

## 🚀 Quick Reference

### Common Commands

```bash
# Deploy infrastructure
cd infrastructure/environments/dev
terraform apply

# Trigger deployment
git push origin main

# Check logs
aws logs tail /ec2/rivet-dev --follow

# Check instance status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names rivet-dev-asg

# Check costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Rollback deployment
aws autoscaling cancel-instance-refresh \
  --auto-scaling-group-name rivet-dev-asg
```

### Quick Links

```
📖 Documentation
├── Quick Start ────────→ QUICKSTART_DEPLOYMENT.md
├── Full Summary ───────→ DEPLOYMENT_UPGRADE_SUMMARY.md
├── CI/CD Guide ────────→ infrastructure/CI_CD_SETUP.md
├── Bedrock Guide ──────→ infrastructure/BEDROCK_MIGRATION.md
├── IAM Reference ──────→ infrastructure/IAM_POLICIES.md
└── Checklist ──────────→ IMPLEMENTATION_CHECKLIST.md

🔧 Tools
├── Terraform ──────────→ infrastructure/environments/dev/
├── GitHub Actions ─────→ .github/workflows/deploy.yml
├── Bedrock Client ─────→ application/src/services/bedrock_client.py
└── Configuration ──────→ application/src/config.py

📊 Monitoring
├── CloudWatch Logs ────→ /ec2/rivet-dev
├── Bedrock Logs ───────→ /aws/bedrock/rivet-dev
├── Cost Explorer ──────→ AWS Console
└── Metrics ────────────→ CloudWatch Dashboard
```

---

**Ready to start?** Follow the visual guide above or jump to [QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md)!
