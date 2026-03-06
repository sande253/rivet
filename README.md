# Rivet — AI-Powered Product Intelligence Platform for Indian Ethnic Wear

> **Transform design sketches into market-ready products with AI analysis, photorealistic mockups, and data-driven insights.**

[![Production](https://img.shields.io/badge/status-live-success)](http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🎯 The Problem

Fashion brands and artisans launching ethnic wear face critical challenges:
- **Inventory Risk**: ₹50K–₹500K lost per failed SKU due to guesswork
- **Slow Market Research**: Manual analysis is time-consuming and subjective
- **Design Uncertainty**: No quick way to validate viability before production
- **Visualization Gap**: Hard to communicate design vision to buyers/manufacturers

## ✨ The Solution

**Rivet** combines AI vision analysis with real market data to predict product viability and generate photorealistic mockups—reducing inventory risk by 40%+ and accelerating time-to-market.

**Upload a sketch → Get instant analysis + realistic mockup → Launch confidently**

---

## 🏗️ Architecture

```
┌─────────────────┐
│   User Upload   │  (PNG, JPG, WEBP sketch)
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│  Claude Vision Analysis  │  (Detect style, features, score)
│  • Market demand (0-20)  │
│  • Uniqueness (0-20)     │
│  • Price fit (0-20)      │
│  • Material appeal (0-20)│
│  • Trend alignment (0-20)│
└────────┬─────────────────┘
         │
    ┌────▼────┐
    │ Score?  │
    └────┬────┘
         │
    ┌────┴──────────────────┐
    │                       │
    ▼                       ▼
  75-100              50-74        0-49
 "LAUNCH"           "MODIFY"   "DO NOT PRODUCE"
    │                  │            │
    ▼                  ▼            ▼
┌─────────────────────────────────────────┐
│  GenAI Tips (Haiku → Sonnet Critique)   │
│  • Draft 3-4 actionable tips            │
│  • Critic evaluates quality             │
│  • Score ≥75 = return to user           │
└────────┬────────────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Bedrock Mockup Gen      │  (IMAGE_VARIATION)
│  • Sketch → Realistic    │
│  • Category-aware        │
│  • S3 storage            │
└──────────────────────────┘
```

---

## 🚀 Features

### 🎨 AI-Powered Analysis
- **Vision Classification**: Claude analyzes sketches against 1000+ real products
- **5-Dimension Scoring**: Market demand, uniqueness, price fit, material, trends
- **Instant Decision**: LAUNCH / MODIFY / DO NOT PRODUCE (2-3 seconds)
- **Grounded Recommendations**: Tips anchored in actual market data

### 🖼️ Photorealistic Mockup Generation
- **Bedrock Titan v2**: IMAGE_VARIATION for sketch-to-photo transformation
- **Category-Specific**: Saree, Lehenga, Salwar Suit, Kurti, Kurta, Sherwani
- **Gender-Aware**: Male/female models based on garment type
- **Anti-Confusion**: Strong negative prompts prevent category mixing
- **Fullscreen View**: Click to expand images in modal

### 🛡️ Production-Grade Resilience
- **Rate Limiting**: 10 analyses/hour, 5 mockups/hour per IP
- **Circuit Breaker**: Auto-fallback if GenAI fails 5× in 60s
- **Caching**: 5-min TTL on GenAI responses
- **Safety Filters**: Profanity detection, PII removal, input validation
- **Cost Control**: Rate limits prevent API abuse

### 🌐 User Experience
- **Bilingual UI**: English & Telugu (Hindi coming soon)
- **Authentication**: Secure login/signup with bcrypt
- **Admin Dashboard**: Proposal management + analytics
- **Responsive Design**: Material Design, mobile-friendly
- **Required Fields**: All form inputs validated

### ☁️ AWS Infrastructure
- **Auto-Scaling**: EC2 instances with ALB
- **RDS PostgreSQL**: User data with automated backups
- **S3 Storage**: Mockup images with presigned URLs
- **Secrets Manager**: Secure credential storage
- **CloudWatch**: Logging and monitoring
- **GitHub Actions**: CI/CD with automated deployments

---

## 📋 Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional, recommended)
- AWS account (for production features)

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/sande253/rivet.git
cd rivet/application

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run development server
flask run
# → http://localhost:5000
```

### Docker Deployment

```bash
cd application
docker-compose up
# → http://localhost:5000
```

### Production Deployment

```bash
# Automated via GitHub Actions on push to main
git push origin main

# Manual deployment
cd infrastructure/environments/prod
terraform init
terraform apply
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `ANTHROPIC_API_KEY` | Claude API access | - | No (Bedrock fallback) |
| `USE_BEDROCK` | Use AWS Bedrock instead of Anthropic | `false` | No |
| `ENVIRONMENT` | `local`, `prod`, `production` | `local` | Yes |
| `DATABASE_URL` | PostgreSQL connection | SQLite | No |
| `S3_BUCKET` | Image storage bucket | - | Prod only |
| `AWS_REGION` | AWS region | `us-east-1` | Prod only |
| `FLASK_SECRET_KEY` | Session encryption | - | Yes |
| `DRAFT_MODEL_ID` | Fast tip generation | `claude-haiku-4-5` | No |
| `CRITIC_MODEL_ID` | Quality evaluation | `claude-sonnet-4-6` | No |
| `BEDROCK_IMAGE_MODEL_ID` | Mockup generation | `amazon.titan-image-generator-v2:0` | No |

### AWS Bedrock Setup

```bash
# Enable Bedrock models in AWS Console
# Required models:
# - Claude 3.5 Sonnet v2
# - Claude 3.5 Haiku
# - Titan Image Generator v2

# IAM role needs:
# - bedrock:InvokeModel
# - s3:PutObject, s3:GetObject
# - secretsmanager:GetSecretValue
```

---

## 📊 Sample Output

```json
{
  "category": "Saree",
  "classification": "LAUNCH",
  "total_score": 82,
  "scores": {
    "market_demand": 18,
    "design_uniqueness": 17,
    "price_competitiveness": 16,
    "material_appeal": 18,
    "trend_alignment": 13
  },
  "detected_style": "Kanjivaram Silk Saree with Gold Border",
  "detected_features": ["silk texture", "gold zari", "traditional weave"],
  "genai_tips": "1. Source premium mulberry silk from Kanchipuram...\n2. Price at ₹1,200–₹1,500 for optimal market fit...",
  "genai_score": 78,
  "genai_model": "claude-sonnet-4-6",
  "genai_latency_ms": 2340,
  "sketch_url": "https://bucket.s3.amazonaws.com/uploads/sketches/abc123.png",
  "mockup_url": "https://bucket.s3.amazonaws.com/uploads/mockups/abc123.png"
}
```

---

## 🧪 Testing

```bash
cd application

# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_genai.py -v

# Test categories
pytest -k "test_market" -v
```

---

## 📁 Project Structure

```
rivet/
├── application/
│   ├── src/
│   │   ├── routes/           # API endpoints
│   │   │   ├── analysis.py   # /analyze, /generate-mockup
│   │   │   ├── admin.py      # Admin dashboard
│   │   │   └── auth.py       # Login/signup
│   │   ├── services/         # Business logic
│   │   │   ├── claude_service.py    # Vision analysis
│   │   │   ├── genai.py             # Draft/Critic pipeline
│   │   │   ├── mockup_service.py    # Image generation
│   │   │   ├── market_service.py    # CSV data loading
│   │   │   ├── cache_service.py     # In-memory cache
│   │   │   ├── circuit_breaker.py   # Resilience
│   │   │   └── safety.py            # Content filtering
│   │   ├── models/           # Database models
│   │   ├── core/             # Extensions (db, limiter)
│   │   ├── config.py         # Flask configuration
│   │   └── app.py            # Application factory
│   ├── templates/            # Jinja2 templates
│   ├── static/               # CSS, JS, images
│   ├── tests/                # Pytest suite
│   ├── data/                 # Market CSVs
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile            # Production image
│   └── docker-compose.yml    # Local development
│
├── infrastructure/           # Terraform IaC
│   ├── modules/
│   │   ├── ec2_prod/         # Auto-scaling EC2
│   │   ├── networking/       # VPC, subnets, ALB
│   │   ├── database/         # RDS PostgreSQL
│   │   ├── storage/          # S3 buckets
│   │   ├── secrets/          # Secrets Manager
│   │   └── bedrock/          # Bedrock permissions
│   └── environments/
│       └── prod/             # Production config
│
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD pipeline
│
└── README.md                 # This file
```

---

## 🎯 Key Achievements

### Technical Excellence
- **Multi-Stage GenAI**: Draft → Critic pipeline with quality gates
- **Production Infrastructure**: Full Terraform + Docker + CI/CD
- **Resilience Patterns**: Circuit breaker, rate limiting, caching
- **Cost Optimization**: Rate limits reduced costs from $20/day to $5-10/day
- **Security**: Bcrypt passwords, IAM roles, no hardcoded secrets

### User Experience
- **Bilingual Support**: English + Telugu
- **Fullscreen Images**: Click-to-expand modal
- **Required Fields**: Form validation prevents incomplete submissions
- **Responsive Design**: Works on mobile, tablet, desktop

### AI Innovation
- **Category-Aware Mockups**: Gender-specific models, anti-confusion prompts
- **Grounded Analysis**: Real market data (1000+ products)
- **Quality Assurance**: Critic model ensures tip quality ≥75/100

---

## 🚫 Known Limitations

- **Static Market Data**: CSVs updated manually (live integration planned)
- **Rate Limits**: 10 analyses/hour may be restrictive for power users
- **Image Size**: 512x512 due to Bedrock Titan constraints
- **Category Confusion**: Kurti sometimes generates as saree (improved with negative prompts)

---

## 🔮 Roadmap

### Q2 2026
- [ ] Live market data integration (Shopify/Amazon scraping)
- [ ] Batch analysis (100 sketches per job)
- [ ] Custom rubrics (luxury vs budget brands)
- [ ] Hindi language support

### Q3 2026
- [ ] ML-based price optimization
- [ ] A/B testing interface (compare design variations)
- [ ] User behavior analytics (track successful launches)
- [ ] Mobile app (React Native)

### Q4 2026
- [ ] Marketplace integration (direct listing to Shopify)
- [ ] Fabric supplier recommendations
- [ ] Trend forecasting (predict next season's winners)

---

## 💰 Cost Breakdown

### Current Production Costs (~$10/day)
- **EC2**: $2.90/day (t3.medium)
- **RDS**: $0.78/day (db.t4g.micro)
- **ALB**: $2.50/day
- **Bedrock API**: $3-5/day (with rate limiting)
- **S3**: $0.10/day

### Cost Optimizations Applied
- Removed dev environment (-$35/month)
- Implemented rate limiting (-50% API costs)
- Deleted NAT Gateway (-$32/month)
- Released unused Elastic IPs (-$3.60/month)

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Sandeep Reddy**
- GitHub: [@sande253](https://github.com/sande253)
- Built for AI for Bharat Hackathon (March 2026)

**Tech Stack**: Flask, PostgreSQL, Claude API, AWS Bedrock, Terraform, Docker, GitHub Actions

---

## 🙏 Acknowledgments

- **Anthropic** for Claude API
- **AWS** for Bedrock and infrastructure
- **AI for Bharat** for the hackathon opportunity
- **Indian artisan community** for inspiration

---

**Production URL**: http://rivet-prod-alb-1684600916.us-east-1.elb.amazonaws.com/

**Repository**: https://github.com/sande253/rivet
