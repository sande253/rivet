# Windows Quick Start Guide

## Current Errors and How to Fix Them

You're seeing these errors because:
1. ❌ Anthropic API key is not set
2. ❌ IAM user lacks permissions for ECS and SSM
3. ✅ Metric filter issue is already fixed (just need to re-init)

## Fix in 3 Steps

### Step 1: Fix IAM Permissions

**Option A - Run PowerShell Script (Easiest)**
```powershell
# Run the fix script
.\fix-permissions.ps1
```

**Option B - Manual via AWS Console**
1. Open AWS Console → IAM → Users → rivet_adm
2. Click "Add permissions" button
3. Select "Attach policies directly"
4. Search for "PowerUserAccess"
5. Check the box next to it
6. Click "Add permissions"

**Option C - AWS CLI Command**
```powershell
aws iam attach-user-policy `
  --user-name rivet_adm `
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### Step 2: Set Your Anthropic API Key

```powershell
# Set the environment variable
$env:TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"

# Verify it's set
echo $env:TF_VAR_anthropic_api_key
```

**Important:** Replace `sk-ant-your-actual-key-here` with your real API key from https://console.anthropic.com/

### Step 3: Deploy Infrastructure

```powershell
# Apply the configuration
terraform apply

# Type 'yes' when prompted
```

## Complete Command Sequence

Copy and paste these commands (replace the API key):

```powershell
# 1. Fix permissions
.\fix-permissions.ps1

# 2. Set API key (REPLACE WITH YOUR ACTUAL KEY)
$env:TF_VAR_anthropic_api_key="AKIA6G3LABFRUQVBCWPO"

# 3. Verify API key is set
echo $env:TF_VAR_anthropic_api_key

# 4. Deploy
terraform apply
```

## Verification

After running the commands above, you should see:

```
Plan: 48 to add, 1 to change, 0 to destroy.

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

Type `yes` and press Enter.

## What If It Still Fails?

### Error: "You must provide either SecretString or SecretBinary"
**Cause:** API key not set
**Fix:**
```powershell
$env:TF_VAR_anthropic_api_key="sk-ant-your-actual-key-here"
terraform apply
```

### Error: "AccessDeniedException" for ECS or SSM
**Cause:** Permissions not attached yet
**Fix:** Wait 30 seconds after attaching the policy, then try again:
```powershell
Start-Sleep -Seconds 30
terraform apply
```

### Error: "The specified log group does not exist"
**Cause:** This shouldn't happen anymore, but if it does:
**Fix:** The metric filters are disabled on first apply. This is expected.

## After Successful Deployment

### Enable Metric Filters (Optional)

After the first successful apply:

1. Open `main.tf` in your editor
2. Find line ~86 with `create_metric_filters = false`
3. Change it to `create_metric_filters = true`
4. Run `terraform apply` again

### Get Your Application URL

```powershell
terraform output app_url
```

### View All Outputs

```powershell
terraform output
```

## Troubleshooting

### Check if API key is set
```powershell
echo $env:TF_VAR_anthropic_api_key
```

### Check IAM permissions
```powershell
aws iam list-attached-user-policies --user-name rivet_adm
```

### Check AWS credentials
```powershell
aws sts get-caller-identity
```

### View Terraform state
```powershell
terraform state list
```

### Clean up and start over (if needed)
```powershell
terraform destroy
terraform apply
```

## Need More Help?

See the detailed troubleshooting guide:
- `TROUBLESHOOTING.md` - Complete error reference
- `README.md` - Full deployment documentation
- `CHECKLIST.md` - Step-by-step deployment checklist

## Quick Reference

```powershell
# Set API key (do this every time you open a new PowerShell window)
$env:TF_VAR_anthropic_api_key="sk-ant-your-key-here"

# Deploy
terraform apply

# View outputs
terraform output

# Destroy everything
terraform destroy
```

## Making API Key Permanent (Optional)

To avoid setting the API key every time:

1. Open PowerShell as Administrator
2. Run:
```powershell
[System.Environment]::SetEnvironmentVariable('TF_VAR_anthropic_api_key', 'sk-ant-your-key-here', 'User')
```
3. Close and reopen PowerShell
4. Verify:
```powershell
echo $env:TF_VAR_anthropic_api_key
```

**Warning:** This stores the key in your Windows user environment variables. Only do this on a secure, personal machine.
