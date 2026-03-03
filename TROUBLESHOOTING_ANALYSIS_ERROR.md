# Troubleshooting: Analysis Page JSON Error

## Error Description

**Error Message**: `Unexpected token '<', "<!DOCTYPE "... is not valid JSON`

**Symptom**: When uploading an image on the analysis page, you get a JSON parsing error, and the mockup output shows the original drawing instead of an enhanced version.

## Root Cause

This error occurs when the frontend expects JSON but receives an HTML error page instead. This typically happens when:

1. The Flask server encounters an unhandled exception
2. The server returns a 500 error page (HTML) instead of JSON
3. The frontend tries to parse the HTML as JSON and fails

## Common Causes

### 1. Missing ANTHROPIC_API_KEY (when USE_BEDROCK=false)

**Symptom**: Error occurs immediately on upload

**Solution**: 
```bash
# Check if API key is set
echo $ANTHROPIC_API_KEY

# If empty and not using Bedrock, set it
export ANTHROPIC_API_KEY="your-api-key-here"

# Or use Bedrock instead (recommended)
export USE_BEDROCK=true
```

### 2. Bedrock Not Configured (when USE_BEDROCK=true)

**Symptom**: Error occurs during analysis

**Solution**:
```bash
# Ensure Bedrock is properly configured
export USE_BEDROCK=true
export AWS_REGION=us-east-1
export DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
export CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1
```

### 3. PIL/Pillow Not Installed (Local Mode)

**Symptom**: Mockup generation fails with "No module named 'PIL'"

**Solution**:
```bash
# Install Pillow
pip install Pillow>=10.0.0

# Or reinstall all requirements
pip install -r requirements.txt
```

### 4. File Upload Issues

**Symptom**: Error occurs before analysis starts

**Solution**:
```bash
# Ensure upload folder exists
mkdir -p static/uploads
mkdir -p static/uploads/sketches
mkdir -p static/uploads/mockups

# Check permissions
chmod 755 static/uploads
```

### 5. Missing Environment Variables

**Symptom**: Various errors depending on what's missing

**Solution**:
```bash
# Check all required environment variables
env | grep -E "FLASK|ANTHROPIC|USE_BEDROCK|AWS|DRAFT|CRITIC"

# Set missing variables
export FLASK_ENV=development
export USE_BEDROCK=true
export GENAI_ENABLED=true
```

## Debugging Steps

### Step 1: Check Flask Logs

```bash
# Run Flask with debug mode
export FLASK_DEBUG=1
flask --app src.wsgi:app run

# Or check logs if running in Docker
docker logs rivet-backend --tail 100 --follow
```

Look for error messages like:
- `KeyError: 'ANTHROPIC_API_KEY'`
- `ModuleNotFoundError: No module named 'PIL'`
- `AccessDeniedException` (Bedrock)
- `FileNotFoundError` (upload folder)

### Step 2: Test API Endpoint Directly

```bash
# Test with curl
curl -X POST http://localhost:8000/analyze \
  -F "sketch=@test_image.jpg" \
  -F "category=saree" \
  -F "description=Test product" \
  -H "Cookie: session=your-session-cookie"

# Check response
# If you get HTML instead of JSON, there's a server error
```

### Step 3: Check Browser Console

Open browser DevTools (F12) and check:

1. **Network Tab**: Look at the `/analyze` request
   - Status code (should be 200, not 500)
   - Response type (should be JSON, not HTML)
   - Response body (check for error messages)

2. **Console Tab**: Look for JavaScript errors
   - JSON parsing errors
   - Network errors
   - CORS errors

### Step 4: Verify Configuration

```python
# In Python shell
from src.app import create_app
app = create_app()

with app.app_context():
    print("USE_BEDROCK:", app.config.get("USE_BEDROCK"))
    print("ANTHROPIC_API_KEY:", "SET" if app.config.get("ANTHROPIC_API_KEY") else "NOT SET")
    print("UPLOAD_FOLDER:", app.config.get("UPLOAD_FOLDER"))
    print("GENAI_ENABLED:", app.config.get("GENAI_ENABLED"))
```

## Solutions by Scenario

### Scenario 1: Running Locally (Development)

```bash
# .env file
FLASK_ENV=development
USE_BEDROCK=false
ANTHROPIC_API_KEY=sk-ant-api03-...
GENAI_ENABLED=true
ENVIRONMENT=local

# Run Flask
flask --app src.wsgi:app run
```

### Scenario 2: Running Locally with Bedrock

```bash
# .env file
FLASK_ENV=development
USE_BEDROCK=true
AWS_REGION=us-east-1
DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
GENAI_ENABLED=true
ENVIRONMENT=local

# Ensure AWS credentials are configured
aws configure

# Run Flask
flask --app src.wsgi:app run
```

### Scenario 3: Running in Docker

```bash
# Check Docker logs
docker logs rivet-backend --tail 100

# Exec into container to check environment
docker exec -it rivet-backend env | grep -E "USE_BEDROCK|ANTHROPIC"

# Restart container with correct environment
docker stop rivet-backend
docker rm rivet-backend

docker run -d \
  --name rivet-backend \
  -p 8000:8000 \
  -e USE_BEDROCK=true \
  -e AWS_REGION=us-east-1 \
  -e DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0 \
  -e CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  -e GENAI_ENABLED=true \
  -e ENVIRONMENT=local \
  your-image:latest
```

### Scenario 4: Running on AWS EC2

```bash
# SSH into EC2 instance
ssh ec2-user@your-instance

# Check Docker logs
docker logs rivet-backend --tail 100

# Check environment variables
docker exec rivet-backend env | grep -E "USE_BEDROCK|AWS"

# Verify IAM role has Bedrock permissions
aws iam get-role-policy \
  --role-name rivet-dev-ec2-role \
  --policy-name rivet-dev-bedrock-invoke
```

## Mockup Issue: Original Drawing Returned

### Cause

The mockup service is running in local mode (PIL enhancement) which only applies basic image filters. This is expected behavior in development.

### Solution 1: Use Production Mode (Bedrock)

```bash
# Set environment to production
export ENVIRONMENT=production
export USE_BEDROCK=true
export BEDROCK_IMAGE_MODEL_ID=amazon.titan-image-generator-v2:0

# Ensure AWS credentials are configured
aws configure

# Restart application
```

### Solution 2: Improve Local Mode Enhancement

The local mode uses PIL to enhance images. To improve results:

```python
# Edit application/src/services/mockup_service.py
# Adjust enhancement parameters in _pil_enhance function

def _pil_enhance(src_path: str, dest_path: str) -> None:
    from PIL import Image, ImageEnhance, ImageFilter

    with Image.open(src_path) as img:
        img = img.convert("RGB")
        
        # Increase enhancement values for more dramatic effect
        img = ImageEnhance.Contrast(img).enhance(1.5)  # Increased from 1.3
        img = ImageEnhance.Color(img).enhance(1.4)     # Increased from 1.2
        img = ImageEnhance.Sharpness(img).enhance(1.6) # Increased from 1.4
        img = ImageEnhance.Brightness(img).enhance(1.1) # Added brightness
        
        # Apply multiple filters
        img = img.filter(ImageFilter.SMOOTH)
        img = img.filter(ImageFilter.DETAIL)
        
        img.save(dest_path, "PNG", quality=95)
```

### Solution 3: Use Bedrock for Image Generation

For realistic mockups, use AWS Bedrock Titan Image Generator:

```bash
# Enable Bedrock image generation
export ENVIRONMENT=production
export BEDROCK_IMAGE_MODEL_ID=amazon.titan-image-generator-v2:0

# Ensure IAM role has permissions
# See infrastructure/IAM_POLICIES.md
```

## Prevention

### 1. Use Environment File

Create `.env` file in application directory:

```bash
# .env
FLASK_ENV=development
USE_BEDROCK=true
AWS_REGION=us-east-1
DRAFT_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
CRITIC_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_IMAGE_MODEL_ID=amazon.titan-image-generator-v2:0
GENAI_ENABLED=true
ENVIRONMENT=local
```

### 2. Add Error Handling

The code has been updated with better error handling:

```python
# API key is now optional when using Bedrock
api_key = current_app.config.get("ANTHROPIC_API_KEY", "")

# Better error messages in mockup service
try:
    result = generate_mockup(...)
except RuntimeError as e:
    return jsonify({"error": str(e)}), 500
```

### 3. Add Health Check Endpoint

Create a health check to verify configuration:

```python
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "use_bedrock": app.config.get("USE_BEDROCK"),
        "genai_enabled": app.config.get("GENAI_ENABLED"),
        "environment": app.config.get("ENVIRONMENT"),
    })
```

## Quick Fix Checklist

- [ ] Check Flask logs for error messages
- [ ] Verify environment variables are set
- [ ] Ensure Pillow is installed (`pip install Pillow`)
- [ ] Check upload folder exists and is writable
- [ ] Verify AWS credentials (if using Bedrock)
- [ ] Check Bedrock model access (if using Bedrock)
- [ ] Test API endpoint directly with curl
- [ ] Check browser console for errors
- [ ] Restart Flask application
- [ ] Clear browser cache

## Still Having Issues?

1. **Enable debug mode**:
   ```bash
   export FLASK_DEBUG=1
   flask --app src.wsgi:app run
   ```

2. **Check full error traceback** in Flask logs

3. **Test with minimal configuration**:
   ```bash
   export USE_BEDROCK=false
   export ANTHROPIC_API_KEY=your-key
   export GENAI_ENABLED=false
   flask --app src.wsgi:app run
   ```

4. **Verify dependencies**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

5. **Check file permissions**:
   ```bash
   ls -la static/uploads/
   ```

## Related Documentation

- [QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md) - Setup guide
- [infrastructure/BEDROCK_MIGRATION.md](infrastructure/BEDROCK_MIGRATION.md) - Bedrock configuration
- [application/.env.example](application/.env.example) - Environment variables

## Support

If you're still experiencing issues after following this guide:

1. Check Flask logs for detailed error messages
2. Review the error traceback
3. Verify all environment variables are set correctly
4. Test with a minimal configuration
5. Check AWS credentials and permissions (if using Bedrock)
