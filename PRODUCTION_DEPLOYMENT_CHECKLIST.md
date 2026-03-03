# Production Deployment Checklist

Use this checklist to ensure a smooth production deployment.

## Pre-Deployment

### Infrastructure Preparation
- [ ] AWS account with appropriate permissions
- [ ] Terraform >= 1.5 installed
- [ ] AWS CLI v2 configured
- [ ] Docker installed locally
- [ ] S3 bucket created for Terraform state
- [ ] Domain name registered (optional, for HTTPS)

### Configuration
- [ ] Copy `terraform.tfvars.example` to `terraform.tfvars`
- [ ] Set AWS region
- [ ] Configure VPC CIDR and subnet CIDRs
- [ ] Set domain name (if using HTTPS)
- [ ] Configure database settings
- [ ] Set instance types and sizes
- [ ] Configure Auto Scaling parameters
- [ ] Set Bedrock model IDs
- [ ] Review cost estimates

### Security Review
- [ ] No hardcoded credentials in code
- [ ] Secrets will be stored in Secrets Manager
- [ ] IAM roles follow least-privilege
- [ ] Security groups properly configured
- [ ] No public IPs on EC2 instances
- [ ] SSH access disabled
- [ ] Encryption enabled (EBS, RDS, S3)

## Deployment

### Phase 1: Infrastructure
- [ ] `cd infrastructure/environments/prod`
- [ ] `terraform init`
- [ ] `terraform validate`
- [ ] `terraform plan` (review carefully)
- [ ] `terraform apply` (takes ~15-20 minutes)
- [ ] Save outputs (ALB DNS, ECR URL, etc.)

### Phase 2: DNS Configuration (if using HTTPS)
- [ ] Note ACM certificate validation records from outputs
- [ ] Add DNS validation records to your domain
- [ ] Wait for certificate validation (~5-10 minutes)
- [ ] Add CNAME record pointing domain to ALB DNS
- [ ] Verify DNS propagation

### Phase 3: Docker Image
- [ ] Get ECR login command from outputs
- [ ] Authenticate Docker to ECR
- [ ] Build production image: `docker build -f Dockerfile.production`
- [ ] Tag image with commit SHA
- [ ] Push image to ECR
- [ ] Verify image in ECR console

### Phase 4: Application Deployment
- [ ] Trigger instance refresh
- [ ] Monitor instance refresh progress
- [ ] Check CloudWatch logs for errors
- [ ] Verify instances are healthy
- [ ] Test application endpoint

### Phase 5: Database Migration (if needed)
- [ ] Export data from SQLite
- [ ] Connect to RDS PostgreSQL
- [ ] Import data to PostgreSQL
- [ ] Verify data integrity
- [ ] Update application to use RDS

## Post-Deployment

### Verification
- [ ] Application accessible via ALB DNS
- [ ] HTTPS working (if configured)
- [ ] HTTP redirects to HTTPS
- [ ] User registration works
- [ ] User login works
- [ ] Image upload works
- [ ] AI analysis works
- [ ] Mockup generation works
- [ ] Database persistence works

### Monitoring Setup
- [ ] CloudWatch logs streaming
- [ ] CloudWatch alarms configured
- [ ] SNS topic created for notifications
- [ ] Email/SMS subscribed to SNS
- [ ] Test alarm triggers
- [ ] Create CloudWatch dashboard

### Performance Testing
- [ ] Load test with expected traffic
- [ ] Monitor CPU/memory usage
- [ ] Check database connections
- [ ] Verify Auto Scaling triggers
- [ ] Test zero-downtime deployment
- [ ] Measure response times

### Security Audit
- [ ] No public IPs on EC2 instances ✓
- [ ] No SSH access enabled ✓
- [ ] Security groups follow least-privilege ✓
- [ ] IMDSv2 required ✓
- [ ] EBS encryption enabled ✓
- [ ] RDS encryption enabled ✓
- [ ] HTTPS enforced ✓
- [ ] Secrets in Secrets Manager ✓
- [ ] IAM roles (no hardcoded credentials) ✓
- [ ] CloudWatch logging enabled ✓

### Backup Verification
- [ ] RDS automated backups enabled
- [ ] Backup retention period set (7 days)
- [ ] Manual snapshot created
- [ ] Test snapshot restore (in non-prod)
- [ ] Document restore procedure

### Documentation
- [ ] Update README with production URL
- [ ] Document deployment process
- [ ] Create runbook for common issues
- [ ] Document disaster recovery procedure
- [ ] Share access with team

## Ongoing Maintenance

### Daily
- [ ] Check CloudWatch alarms
- [ ] Review error logs
- [ ] Monitor application performance

### Weekly
- [ ] Review CloudWatch metrics
- [ ] Check Auto Scaling activity
- [ ] Review RDS performance
- [ ] Check disk usage
- [ ] Review costs

### Monthly
- [ ] Review and optimize costs
- [ ] Update dependencies
- [ ] Review security groups
- [ ] Test disaster recovery
- [ ] Update documentation

### Quarterly
- [ ] Review and update alarms
- [ ] Performance tuning
- [ ] Capacity planning
- [ ] Security audit
- [ ] Cost optimization review

## Rollback Plan

If deployment fails:

### Immediate Rollback
1. [ ] Revert to previous Docker image tag
2. [ ] Trigger instance refresh with old image
3. [ ] Monitor for stability
4. [ ] Investigate root cause

### Database Rollback
1. [ ] Stop application
2. [ ] Restore RDS from snapshot
3. [ ] Update connection string
4. [ ] Restart application
5. [ ] Verify data integrity

### Complete Rollback
1. [ ] `terraform destroy` (if needed)
2. [ ] Restore from previous Terraform state
3. [ ] Redeploy from known-good configuration

## Emergency Contacts

- **AWS Support**: [Support Plan Level]
- **Team Lead**: [Name, Phone, Email]
- **DevOps**: [Name, Phone, Email]
- **Database Admin**: [Name, Phone, Email]
- **Security Team**: [Name, Phone, Email]

## Success Criteria

Deployment is successful when:
- [ ] All infrastructure deployed without errors
- [ ] Application accessible via HTTPS
- [ ] All features working correctly
- [ ] No errors in CloudWatch logs
- [ ] All health checks passing
- [ ] Auto Scaling working correctly
- [ ] Database connections stable
- [ ] Monitoring and alarms active
- [ ] Backups configured and tested
- [ ] Team trained on new infrastructure

## Sign-Off

- [ ] Infrastructure Engineer: _________________ Date: _______
- [ ] Application Developer: _________________ Date: _______
- [ ] Security Engineer: _________________ Date: _______
- [ ] Project Manager: _________________ Date: _______

---

**Notes:**
- Keep this checklist updated as infrastructure evolves
- Document any deviations from the plan
- Share lessons learned with the team
- Update runbooks based on issues encountered
