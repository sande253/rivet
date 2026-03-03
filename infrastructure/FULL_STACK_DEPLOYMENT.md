# Rivet Full Stack Deployment Guide

## Architecture Overview

This deployment creates a complete full-stack application on AWS:

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Amplify    │         │   Cognito    │                      │
│  │  (Frontend)  │◄────────┤  User Pool   │                      │
│  └──────┬───────┘         └──────────────┘                      │
│         │                                                         │
│         │ API Calls                                              │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │     ALB      │                                                │
│  │  (Port 80)   │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         │ Routes to                                              │
│         ▼                                                         │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │  EC2 (ASG)   │◄────────┤     ECR      │                      │
│  │   Docker     │         │ (Image Repo) │                      │
│  └──────┬───────┘         └──────────────┘                      │
│         │                                                         │
│         │ Uses                                                    │
│         ▼                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Bedrock    │  │      S3      │  │   Secrets    │          │
│  │  (AI/ML)     │  │  (Uploads)   │  │   Manager    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Current Status

### ✅ Already Deployed (from previous steps)
- VPC and networking
- S3 bucket for uploads
- Secrets Manager (Anthropic API key)
- SSM Parameters (model IDs)
- Bedrock IAM permissions
- CloudWatch logs and alarms
- Application Load Balancer
- ECS cluster (will be replaced with EC2)

### 🔄 Changes Required
1. **Replace ECS with EC2** - Use Auto Scaling Group with Docker
2. **Update Dockerfile** - Use Gunicorn with Uvicorn workers
3. **Add Cognito** - User authentication
4. **Add Amplify** - Frontend hosting (optional, app is monolithic)

## Important Note About Application Architecture

**Current Application**: This is a **monolithic Flask application** that serves HTML templates directly. It's NOT separated into frontend/backend.

**Amplify Consideration**: Since the application serves templates from Flask, Amplify hosting is **optional** and would require:
- Extracting frontend to separate React/Vue/Angular app
- Converting Flask to API-only mode
- Significant code changes (which you want to avoid)

**Recommended Approach**: 
- Deploy Flask app on EC2 (serves both frontend and backend)
- Add Cognito for authentication (integrate with Flask-Login)
- Skip Amplify for now (or use for future frontend separation)

## Deployment Steps

### Phase 1: Update Application for EC2

#### 1.1 Update Dockerfile
```bash
# Use the new production Dockerfile
cp application/Dockerfile application/Dockerfile.backup
cp application/Dockerfile.production application/Dockerfile
```

#### 1.2 Update requirements.txt
Add Uvicorn to requirements.txt:
```bash
cd application
echo "uvicorn[standard]>=0.24.0" >> requirements.txt
```

#### 1.3 Build and Push to ECR
```powershell
# Build with new Dockerfile
docker build -t rivet-dev -f Dockerfile.production .

# Tag and push
$ECR_URL = "976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev"
docker tag rivet-dev:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Phase 2: Deploy EC2 Infrastructure

#### 2.1 Create EC2 Module Files

I've created:
- `infrastructure/modules/ec2/main.tf` - EC2 instances with Auto Scaling
- `infrastructure/modules/ec2/user_data.sh` - Bootstrap script
- `infrastructure/modules/ec2/variables.tf` - (need to create)
- `infrastructure/modules/ec2/outputs.tf` - (need to create)

#### 2.2 Create Cognito Module

Create `infrastructure/modules/cognito/` with:
- User Pool
- App Client
- Domain
- Groups (admin, user)

#### 2.3 Update Main Configuration

Modify `infrastructure/environments/dev/main.tf` to:
- Add EC2 module (replace ECS)
- Add Cognito module
- Update dependencies

### Phase 3: Deploy

```powershell
cd infrastructure/environments/dev

# Initialize new modules
terraform init -upgrade

# Review changes
terraform plan

# Apply
terraform apply
```

## Detailed Module Specifications

### EC2 Module

**Features**:
- Amazon Linux 2023 AMI (latest)
- Auto Scaling Group (min: 1, max: 3, desired: 1)
- Launch Template with user data
- IAM role with ECR, Secrets Manager, Bedrock access
- Security group (ALB → EC2 only)
- CloudWatch monitoring
- Auto-scaling based on CPU (scale up >70%, scale down <30%)

**User Data Script**:
1. Install Docker
2. Authenticate to ECR using IAM role
3. Pull Docker image
4. Retrieve secrets from Secrets Manager
5. Run container with environment variables
6. Configure CloudWatch logs
7. Health check

### Cognito Module

**Features**:
- User Pool with email verification
- App Client for web application
- Custom domain (optional)
- User groups: admin, user
- Password policy
- MFA optional

**Integration with Flask**:
- Use Flask-Cognito or custom integration
- Replace Flask-Login with Cognito tokens
- Requires code changes (minimal)

### Amplify Module (Optional)

**Only if separating frontend**:
- Connect to GitHub repository
- Build settings for React/Vue/Angular
- Environment variables (API URL)
- Custom domain
- Branch deployments

## Cost Estimate

### Additional Costs (compared to ECS)

**EC2 (t3.small)**:
- Instance: $15/month (1 instance, 24/7)
- EBS: $2/month (20GB)
- Data transfer: $5/month

**Cognito**:
- First 50,000 MAUs: Free
- Additional: $0.0055 per MAU

**Amplify** (if used):
- Build: $0.01 per build minute
- Hosting: $0.15 per GB served
- Typical: $5-10/month

**Total Additional**: ~$25-30/month

**Total Infrastructure**: ~$100-120/month

## Migration from ECS to EC2

### Why EC2 Instead of ECS?

**Advantages**:
- Direct Docker control
- Simpler debugging
- Lower cost for single instance
- Easier to customize
- No task definition complexity

**Disadvantages**:
- Manual container management
- Less automated scaling
- Need to manage OS updates

### Migration Steps

1. **Build new Docker image** with Uvicorn workers
2. **Deploy EC2 infrastructure** alongside ECS
3. **Test EC2 deployment** via ALB
4. **Update ALB target group** to point to EC2
5. **Destroy ECS resources** after verification

## Security Considerations

### IAM Roles
- ✅ No hardcoded credentials
- ✅ EC2 instance profile with minimal permissions
- ✅ Secrets retrieved from Secrets Manager
- ✅ SSM parameters for configuration

### Network Security
- ✅ EC2 in private subnets
- ✅ ALB in public subnets
- ✅ Security groups restrict traffic
- ✅ No SSH access (use Systems Manager Session Manager if needed)

### Application Security
- ✅ Non-root user in Docker
- ✅ IMDSv2 required
- ✅ Encrypted secrets
- ✅ HTTPS ready (add ACM certificate)

## Monitoring

### CloudWatch Logs
- `/ec2/rivet-dev` - Application logs
- `/aws/bedrock/rivet-dev` - Bedrock logs

### CloudWatch Metrics
- EC2 CPU utilization
- ALB request count
- Target health
- GenAI latency and errors

### CloudWatch Alarms
- CPU high (>70%) - triggers scale up
- CPU low (<30%) - triggers scale down
- GenAI high latency
- GenAI error rate

## Troubleshooting

### EC2 Instance Won't Start
```powershell
# Check user data logs
aws ssm start-session --target i-xxxxx
sudo cat /var/log/user-data.log
```

### Docker Container Won't Start
```powershell
# SSH to instance (via Session Manager)
aws ssm start-session --target i-xxxxx

# Check Docker logs
sudo docker logs rivet-backend

# Check if image was pulled
sudo docker images
```

### Application Not Accessible
```powershell
# Check target group health
aws elbv2 describe-target-health --target-group-arn <arn>

# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx
```

## Next Steps

1. **Complete EC2 module files** (variables.tf, outputs.tf)
2. **Create Cognito module** (if authentication needed)
3. **Update main.tf** to use EC2 instead of ECS
4. **Test deployment** in dev environment
5. **Add HTTPS** with ACM certificate
6. **Consider frontend separation** for Amplify (future)

## Files Created

✅ `application/Dockerfile.production` - Production Dockerfile with Uvicorn  
✅ `application/.dockerignore` - Docker ignore file  
✅ `infrastructure/modules/ec2/main.tf` - EC2 infrastructure  
✅ `infrastructure/modules/ec2/user_data.sh` - Bootstrap script  
⏳ `infrastructure/modules/ec2/variables.tf` - Need to create  
⏳ `infrastructure/modules/ec2/outputs.tf` - Need to create  
⏳ `infrastructure/modules/cognito/` - Need to create  
⏳ Update `infrastructure/environments/dev/main.tf` - Need to update  

## Decision Required

**Question**: Do you want to:

**Option A**: Deploy with EC2 only (recommended for monolithic app)
- Keep Flask serving templates
- Add Cognito for auth (optional)
- Skip Amplify
- Faster deployment
- No code changes

**Option B**: Full separation (requires code changes)
- Extract frontend to separate app
- Convert Flask to API-only
- Deploy frontend on Amplify
- Add Cognito
- More complex but better architecture

**Recommendation**: Start with Option A, then migrate to Option B later if needed.

Would you like me to complete the EC2 deployment (Option A)?
