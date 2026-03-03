# 🚀 Next Steps - Deploy Your Application

## ✅ Infrastructure: COMPLETE (49 resources deployed)
## ⏳ Application: PENDING (needs Docker image)

---

## What You Need to Do Now

Your AWS infrastructure is ready, but the application isn't running yet because there's no Docker image in ECR.

---

## Quick Deploy (Copy & Paste These Commands)

### 1. Navigate to Application Directory
```powershell
cd ..\..\..\application
```

### 2. Build Docker Image
```powershell
docker build -t rivet-dev .
```

### 3. Login to ECR
```powershell
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 976792586595.dkr.ecr.us-east-1.amazonaws.com
```

### 4. Tag and Push Image
```powershell
docker tag rivet-dev:latest 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev:latest
docker push 976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev:latest
```

### 5. Deploy to ECS
```powershell
aws ecs update-service --cluster rivet-dev --service rivet-dev-service --force-new-deployment --region us-east-1
```

### 6. Wait 2-5 Minutes, Then Test
```powershell
# Test the application
curl http://rivet-dev-alb-1505746224.us-east-1.elb.amazonaws.com

# Or open in browser
start http://rivet-dev-alb-1505746224.us-east-1.elb.amazonaws.com
```

---

## ⏱️ Timeline

- **Build Docker image**: 2-5 minutes
- **Push to ECR**: 1-3 minutes
- **ECS deployment**: 2-5 minutes
- **Total**: ~10 minutes

---

## 🎯 Your Application URL

Once deployed, your application will be available at:
```
http://rivet-dev-alb-1505746224.us-east-1.elb.amazonaws.com
```

---

## 📊 What's Already Done

✅ VPC and networking  
✅ S3 bucket for uploads  
✅ ECS cluster  
✅ Application Load Balancer  
✅ IAM roles and policies  
✅ Secrets Manager (API key)  
✅ SSM parameters (model IDs)  
✅ CloudWatch logs and alarms  
✅ Bedrock IAM permissions  

---

## ❌ What's Pending

❌ Docker image in ECR  
❌ ECS tasks running  
❌ Application accessible  

---

## 🔍 Verify Deployment

### Check if image is in ECR
```powershell
aws ecr describe-images --repository-name rivet-dev --region us-east-1
```

### Check ECS service status
```powershell
aws ecs describe-services --cluster rivet-dev --services rivet-dev-service --region us-east-1 --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### View application logs
```powershell
aws logs tail /ecs/rivet-dev --follow --region us-east-1
```

---

## 🆘 Troubleshooting

### Docker build fails
**Check**: Do you have Docker Desktop installed and running?
```powershell
docker --version
docker ps
```

### ECR login fails
**Check**: AWS credentials are configured
```powershell
aws sts get-caller-identity
```

### ECS tasks won't start
**Check**: View logs for errors
```powershell
aws logs tail /ecs/rivet-dev --since 30m --region us-east-1
```

### Application returns 503
**Wait**: ECS tasks take 2-5 minutes to become healthy
**Check**: Target group health
```powershell
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:976792586595:targetgroup/rivet-dev-tg/e261ca11d9d35178
```

---

## 📚 Documentation

- **DEPLOYMENT_COMPLETE.md** - Full deployment summary
- **README.md** - Complete guide
- **TROUBLESHOOTING.md** - Error solutions

---

## 🎉 After Deployment

Once your application is running:

1. **Test the API** - Upload a product image and get analysis
2. **Check logs** - Monitor CloudWatch for any errors
3. **Enable metrics** - Set `create_metric_filters = true` in main.tf
4. **Monitor costs** - Check AWS Cost Explorer
5. **Scale if needed** - Adjust `desired_count` in terraform.tfvars

---

**Ready? Start with Step 1 above!**
