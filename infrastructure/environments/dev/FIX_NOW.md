# 🚨 IMMEDIATE FIX REQUIRED

## You Have 2 Issues to Fix Before Deployment

### ❌ Issue 1: Missing API Key
The Anthropic API key environment variable is not set.

### ❌ Issue 2: Missing IAM Permissions
User `rivet_adm` lacks permissions for ECS and SSM.

---

## ✅ SOLUTION (Copy & Paste These Commands)

### Step 1: Fix IAM Permissions
```powershell
# Run this command in PowerShell
aws iam attach-user-policy --user-name rivet_adm --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

**OR** use the automated script:
```powershell
.\fix-permissions.ps1
```

### Step 2: Set API Key
```powershell
# Replace with your actual API key from https://console.anthropic.com/
$env:TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"

# Verify it's set
echo $env:TF_VAR_anthropic_api_key
```

### Step 3: Deploy
```powershell
terraform apply
```

---

## 📋 Complete Copy-Paste Solution

```powershell
# 1. Fix permissions
aws iam attach-user-policy --user-name rivet_adm --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# 2. Set API key (REPLACE WITH YOUR ACTUAL KEY!)
$env:TF_VAR_anthropic_api_key="sk-ant-PUT-YOUR-REAL-KEY-HERE"

# 3. Verify
echo $env:TF_VAR_anthropic_api_key

# 4. Deploy
terraform apply
```

---

## ⏱️ Expected Timeline

- **Step 1 (Permissions):** 10 seconds
- **Step 2 (API Key):** 5 seconds  
- **Step 3 (Deploy):** 8-10 minutes

**Total:** ~10 minutes

---

## ✅ Success Indicators

You'll know it's working when you see:
```
Plan: 48 to add, 1 to change, 0 to destroy.

Do you want to perform these actions?
  Enter a value: yes
```

After typing `yes`, you'll see resources being created:
```
module.networking.aws_vpc.main: Creating...
module.storage.aws_s3_bucket.uploads: Creating...
module.secrets.aws_secretsmanager_secret.anthropic_api_key: Creating...
...
```

---

## 🆘 Still Having Issues?

### If you see "AccessDeniedException"
Wait 30 seconds for IAM to propagate, then try again:
```powershell
Start-Sleep -Seconds 30
terraform apply
```

### If you see "You must provide either SecretString or SecretBinary"
Your API key is not set. Run:
```powershell
$env:TF_VAR_anthropic_api_key="sk-ant-your-key-here"
terraform apply
```

### If you see "The specified log group does not exist"
This is already fixed in the code. Just run `terraform apply` again.

---

## 📚 More Help

- **Windows Guide:** `WINDOWS_QUICKSTART.md`
- **Detailed Troubleshooting:** `TROUBLESHOOTING.md`
- **Full Documentation:** `README.md`

---

## 🎯 Quick Checklist

- [ ] IAM permissions attached (PowerUserAccess)
- [ ] API key set in environment variable
- [ ] API key verified with `echo $env:TF_VAR_anthropic_api_key`
- [ ] Run `terraform apply`
- [ ] Type `yes` when prompted

**That's it! You're ready to deploy.**
