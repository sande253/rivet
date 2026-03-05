# Deployment Checklist

## ✅ Code Pushed
Commit: `7dcb01d` - "refactor: split monolithic index.html into separate page templates"

## Monitor Deployment

### 1. GitHub Actions
Check: https://github.com/sande253/rivet/actions

The workflow should:
- ✓ Build Docker image
- ✓ Push to ECR
- ✓ Update ECS service
- ✓ Wait for deployment to complete

### 2. ECS Service Update
Once GitHub Actions completes, check ECS:
```bash
aws ecs describe-services \
  --cluster rivet-prod-cluster \
  --services rivet-prod-service \
  --query 'services[0].deployments' \
  --region us-east-1
```

Look for:
- New deployment with `desiredCount: 1`
- Old deployment draining
- `runningCount` should become 1 for new deployment

### 3. Instance Refresh
The new task will:
- Pull latest Docker image with refactored templates
- Start with new code
- Register with ALB
- Pass health checks
- Old task will be stopped

### 4. Test Production

Once deployed, test these URLs:
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/analyze
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/market
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/how
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/account
- http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/analyses

### 5. Verify Functionality

Test in production:
- ✓ Navigation works (click between pages)
- ✓ Home page displays correctly
- ✓ Analyze form works
- ✓ Submit an analysis
- ✓ Generate a mockup
- ✓ Check market page
- ✓ Language switching works
- ✓ Mobile view works
- ✓ User dropdown works
- ✓ Browser back/forward buttons work

### 6. Check Logs

If any issues:
```bash
# Get task ARN
aws ecs list-tasks \
  --cluster rivet-prod-cluster \
  --service-name rivet-prod-service \
  --region us-east-1

# Get logs
aws logs tail /ecs/rivet-prod --follow --region us-east-1
```

## Rollback Plan (if needed)

If issues occur:

### Option 1: Git Revert
```bash
git revert 7dcb01d
git push origin main
# Wait for automatic deployment
```

### Option 2: Manual Rollback
1. Restore old code:
   ```bash
   git checkout 9df4929  # Previous commit
   git checkout -b rollback
   git push origin rollback
   ```

2. Update ECS to use previous image tag

### Option 3: Quick Fix
If minor issue, fix and push:
```bash
# Make fix
git add .
git commit -m "fix: [description]"
git push origin main
```

## Expected Timeline

- GitHub Actions: ~3-5 minutes
- ECS deployment: ~2-3 minutes
- Health checks: ~1 minute
- Total: ~6-9 minutes

## Success Criteria

✅ GitHub Actions workflow completes successfully
✅ ECS service shows 1 running task with new deployment
✅ ALB health checks pass
✅ All pages load correctly
✅ Navigation works
✅ Analysis workflow completes
✅ No console errors
✅ Mobile view works

## Notes

- This is a structural refactor with zero visual changes
- All functionality preserved
- Original file backed up as `index_backup.html`
- Can rollback easily if needed
- Monitor for ~10 minutes after deployment
