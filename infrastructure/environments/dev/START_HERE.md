# 🚀 START HERE - Deploy Rivet in 2 Steps

## You're Almost There!

Good news: IAM permissions are fixed and most resources are already created. You just need to set your API key and finish the deployment.

---

## ✅ Step 1: Set Your API Key

**Option A - Use the Helper Script (Easiest)**
```powershell
.\deploy.ps1
```
The script will prompt you for your API key and deploy automatically.

**Option B - Manual**
```powershell
# Set your API key (get it from https://console.anthropic.com/)
$env:TF_VAR_anthropic_api_key="ZQprusuP59gsd0Cq8hEpt/jtMs0KlzUxlr7k+L/o"

# Verify it's set
echo $env:TF_VAR_anthropic_api_key

# Deploy
terraform apply
```

---

## ✅ Step 2: Type 'yes' When Prompted

You'll see:
```
Plan: 3 to add, 0 to change, 1 to destroy.

Do you want to perform these actions?
  Enter a value: yes
```

Type `yes` and press Enter.

---

## 🎉 That's It!

The deployment will complete in about 2 minutes. You'll see:
```
Apply complete! Resources: 3 added, 0 changed, 1 destroyed.

Outputs:

app_url = "http://rivet-dev-alb-xxxxxxxxx.us-east-1.elb.amazonaws.com"
ecr_repository_url = "976792586595.dkr.ecr.us-east-1.amazonaws.com/rivet-dev"
...
```

---

## 📊 Current Status

✅ VPC and networking created  
✅ S3 bucket created  
✅ ECS cluster created  
✅ ALB created  
✅ IAM roles and policies created  
✅ SSM parameters created  
✅ CloudWatch logs created  
❌ API key needs to be set (that's what you're doing now!)

---

## 🆘 Troubleshooting

### "You must provide either SecretString or SecretBinary"
**Cause:** API key not set  
**Fix:** Run `.\deploy.ps1` or set `$env:TF_VAR_anthropic_api_key="sk-ant-your-key"`

### "Invalid API key format"
**Cause:** API key doesn't start with `sk-ant-`  
**Fix:** Get the correct key from https://console.anthropic.com/

### Script won't run
**Cause:** PowerShell execution policy  
**Fix:** Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first

---

## 📚 After Deployment

Once deployment completes, see:
- `README.md` - Build and deploy your Docker image
- `QUICK_REFERENCE.md` - Common commands
- `CHECKLIST.md` - Post-deployment steps

---

## 🎯 Quick Commands

```powershell
# Deploy with helper script
.\deploy.ps1

# Or deploy manually
$env:TF_VAR_anthropic_api_key="sk-ant-your-key-here"
terraform apply

# View outputs
terraform output

# Get application URL
terraform output app_url
```

---

**Ready? Run `.\deploy.ps1` now!**
