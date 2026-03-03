# Debug Quick Reference

Quick commands and checks for common issues.

## 🔍 Check Application Status

```bash
# Check if Flask is running
curl http://localhost:8000/

# Check health (if endpoint exists)
curl http://localhost:8000/health

# Check logs
tail -f logs/app.log  # or wherever your logs are
```

## 🔧 Environment Variables

```bash
# Check all environment variables
env | grep -E "FLASK|USE_BEDROCK|ANTHROPIC|AWS|DRAFT|CRITIC|GENAI"

# Check specific variables
echo $USE_BEDROCK
echo $ANTHROPIC_API_KEY
echo $AWS_REGION
```

## 🐍 Python Shell Debugging

```python
# Start Python shell
python

# Import and check config
from application.src.app import create_app
app = create_app()

with app.app_context():
    print("USE_BEDROCK:", app.config.get("USE_BEDROCK"))
    print("API_KEY:", "SET" if app.config.get("ANTHROPIC_API_KEY") else "NOT SET")
    print("ENVIRONMENT:", app.config.get("ENVIRONMENT"))
    print("GENAI_ENABLED:", app.config.get("GENAI_ENABLED"))
    print("UPLOAD_FOLDER:", app.config.get("UPLOAD_FOLDER"))
```

## 🔐 AWS Credentials

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test Bedrock invocation
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-haiku-20241022-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --region us-east-1 \
  output.json
```

## 📦 Dependencies

```bash
# Check if Pillow is installed
python -c "import PIL; print(PIL.__version__)"

# Check if boto3 is installed
python -c "import boto3; print(boto3.__version__)"

# Reinstall all dependencies
pip install -r requirements.txt --upgrade
```

## 📁 File Permissions

```bash
# Check upload folder
ls -la static/uploads/

# Create folders if missing
mkdir -p static/uploads/sketches
mkdir -p static/uploads/mockups

# Fix permissions
chmod 755 static/uploads
chmod 755 static/uploads/sketches
chmod 755 static/uploads/mockups
```

## 🐳 Docker Debugging

```bash
# Check container status
docker ps -a | grep rivet

# Check container logs
docker logs rivet-backend --tail 100 --follow

# Exec into container
docker exec -it rivet-backend bash

# Check environment inside container
docker exec rivet-backend env | grep -E "USE_BEDROCK|ANTHROPIC"

# Restart container
docker restart rivet-backend
```

## 🌐 API Testing

```bash
# Test analyze endpoint (requires authentication)
curl -X POST http://localhost:8000/analyze \
  -F "sketch=@test_image.jpg" \
  -F "category=saree" \
  -F "description=Test product" \
  -H "Cookie: session=your-session-cookie"

# Test mockup endpoint
curl -X POST http://localhost:8000/generate-mockup \
  -F "sketch=@test_image.jpg" \
  -F "category=saree" \
  -F "description=Test product" \
  -H "Cookie: session=your-session-cookie"
```

## 🔍 Common Error Patterns

### "Unexpected token '<', '<!DOCTYPE'..."
```bash
# This means server returned HTML instead of JSON
# Check Flask logs for the actual error
tail -f logs/app.log

# Common causes:
# 1. Missing ANTHROPIC_API_KEY (when USE_BEDROCK=false)
# 2. Bedrock not configured (when USE_BEDROCK=true)
# 3. Missing Pillow (for local mockup)
```

### "KeyError: 'ANTHROPIC_API_KEY'"
```bash
# Set the API key or use Bedrock
export USE_BEDROCK=true
# OR
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### "ModuleNotFoundError: No module named 'PIL'"
```bash
# Install Pillow
pip install Pillow>=10.0.0
```

### "AccessDeniedException" (Bedrock)
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# Verify IAM permissions
aws iam get-role-policy \
  --role-name your-role-name \
  --policy-name bedrock-invoke
```

## 🔄 Quick Fixes

### Reset Everything
```bash
# Stop Flask
pkill -f flask

# Clear cache
rm -rf __pycache__
rm -rf application/src/__pycache__
rm -rf application/src/*/__pycache__

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Restart Flask
flask --app application.src.wsgi:app run
```

### Use Minimal Configuration
```bash
# Create minimal .env
cat > .env << EOF
FLASK_ENV=development
USE_BEDROCK=false
ANTHROPIC_API_KEY=your-key-here
GENAI_ENABLED=false
ENVIRONMENT=local
EOF

# Restart Flask
flask --app application.src.wsgi:app run
```

### Test Without GenAI
```bash
# Disable GenAI temporarily
export GENAI_ENABLED=false

# Restart Flask
flask --app application.src.wsgi:app run
```

## 📊 Monitoring

```bash
# Watch logs in real-time
tail -f logs/app.log | grep -E "ERROR|WARNING|Exception"

# Check memory usage
ps aux | grep flask

# Check disk space
df -h

# Check network connections
netstat -an | grep 8000
```

## 🎯 Quick Test Script

```bash
#!/bin/bash
# save as test.sh and run: bash test.sh

echo "=== Environment Check ==="
echo "USE_BEDROCK: $USE_BEDROCK"
echo "FLASK_ENV: $FLASK_ENV"
echo "AWS_REGION: $AWS_REGION"

echo -e "\n=== Python Packages ==="
python -c "import PIL; print('Pillow:', PIL.__version__)" 2>&1
python -c "import boto3; print('boto3:', boto3.__version__)" 2>&1
python -c "import flask; print('Flask:', flask.__version__)" 2>&1

echo -e "\n=== AWS Credentials ==="
aws sts get-caller-identity 2>&1 | head -5

echo -e "\n=== File Permissions ==="
ls -la static/uploads/ 2>&1 | head -5

echo -e "\n=== Flask Status ==="
curl -s http://localhost:8000/ | head -5

echo -e "\n=== Done ==="
```

## 📝 Log Locations

```bash
# Flask development server
# Logs to stdout/stderr

# Docker container
docker logs rivet-backend

# AWS EC2 CloudWatch
aws logs tail /ec2/rivet-dev --follow

# Application logs (if configured)
tail -f logs/app.log
tail -f logs/error.log
```

## 🆘 Emergency Commands

```bash
# Kill all Flask processes
pkill -9 -f flask

# Remove all Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Reset virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Reset database (SQLite)
rm -f instance/rivet.db
flask --app application.src.wsgi:app shell
>>> from application.src.core.extensions import db
>>> db.create_all()
>>> exit()
```

## 📞 Get Help

1. Check [TROUBLESHOOTING_ANALYSIS_ERROR.md](TROUBLESHOOTING_ANALYSIS_ERROR.md)
2. Review Flask logs for detailed errors
3. Test with minimal configuration
4. Check AWS credentials and permissions
5. Verify all dependencies are installed

## 🔗 Related Documentation

- [TROUBLESHOOTING_ANALYSIS_ERROR.md](TROUBLESHOOTING_ANALYSIS_ERROR.md) - Detailed troubleshooting
- [application/.env.example](application/.env.example) - Environment variables
- [QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md) - Setup guide
- [infrastructure/BEDROCK_MIGRATION.md](infrastructure/BEDROCK_MIGRATION.md) - Bedrock configuration
