# Rivet — AI-Powered Product Viability Assessment for Indian Ethnic Wear

> **Transform design sketches into market-ready products in minutes using AI analysis and photorealistic mockups.**

---

## 🎯 The Problem

Fashion brands launching ethnic wear face a critical challenge:
- Inventory decisions based on guesswork, not data
- High cost of unsold stock (₹50K–₹500K per failed SKU)
- Manual market research is slow and subjective
- No quick way to evaluate design viability before production

## ✨ The Solution

**Rivet** is an AI-powered tool that analyzes product sketches against real market data to **predict viability and reduce inventory risk by 40%+**.

**Upload a sketch → Get instant analysis + photorealistic mockup → Launch confidently**

---

## 🏗️ Architecture

```
┌─────────────────┐
│   User Upload   │  (PNG, JPG, WEBP)
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│  Claude Vision Analysis  │  (Vision: detect style, features, score)
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
│  GenAI Tips (Haiku → Sonnet Critique)   │  (Only if MODIFY+)
│  • Draft 3-4 actionable tips            │
│  • Critic evaluates quality             │
│  • Score ≥75 = return to user           │
└────────┬────────────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Generate Mockup         │  (Sketch → Realistic product photo)
│  • Local: PIL enhance    │
│  • Prod: Bedrock Titan   │
│  • Upload to S3 / serve  │
└──────────────────────────┘
```

---

## 🚀 Features

### Core Analysis
- **Vision-Powered Classification**: Claude analyzes sketches against 1000+ real market products
- **5-Dimension Scoring**: Market demand, uniqueness, price fit, material, trends
- **Instant Decision**: LAUNCH / MODIFY / DO NOT PRODUCE (within 2-3 seconds)

### GenAI Improvement Tips
- **Two-Stage Pipeline**: Draft generation → Critic evaluation
- **Quality Threshold**: Only tips scoring ≥75/100 returned
- **Grounded Context**: Recommendations anchored in real market data

### Mockup Generation
- **Sketch → Realistic Photo**: Bedrock IMAGE_VARIATION or PIL enhancement
- **Category-Aware**: Saree, Lehenga, Salwar Suit, Kurti
- **Production Ready**: S3 integration for scalability

### Resilience
- **Circuit Breaker**: Auto-fallback if GenAI fails 5× in 60s
- **Caching**: 5-min TTL on GenAI responses
- **Safety Checks**: Profanity filter, PII removal, input validation

### User Experience
- **Bilingual UI**: English & Telugu
- **Authentication**: Login/signup with secure sessions
- **Admin Dashboard**: Proposal management + analytics
- **Professional Styling**: Material Design, responsive layout

---

## 📋 Quick Start

### Prerequisites
- Python 3.11+
- `uv` package manager (or pip)
- Docker (optional, recommended for prod)

### Local Development

```bash
# 1. Clone & navigate
cd application

# 2. Copy .env template
cp .env.example .env

# 3. Add your API keys to .env
ANTHROPIC_API_KEY=sk-ant-...
FLASK_DEBUG=1
FLASK_ENV=development

# 4. Install dependencies
uv pip install -r requirements.txt

# 5. Run Flask dev server
flask run
# → http://localhost:5000
```

### First Run
1. **Sign up** with any email/password
2. **Upload a product sketch** (PNG, JPG, WEBP)
3. **Select category** (Saree, Lehenga, etc.)
4. **Click "Run Analysis"** → See instant results
5. **(Optional) Generate Mockup** → See realistic product photo

### Docker (Production-like)
```bash
cd application
docker build -t rivet .
docker run -p 5000:5000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e FLASK_ENV=production \
  rivet
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API access | (required) |
| `FLASK_ENV` | Environment mode | `development` |
| `DRAFT_MODEL_ID` | Fast tip generation | `claude-haiku-4-5-20251001` |
| `CRITIC_MODEL_ID` | Quality evaluation | `claude-sonnet-4-6` |
| `DATABASE_URL` | SQLite or PostgreSQL | `sqlite:///instance/rivet.db` |
| `GENAI_CACHE_TTL` | Cache duration (seconds) | `300` |
| `ENVIRONMENT` | `local` or `production` | `local` |

**Production (AWS Bedrock + S3):**
```bash
ENVIRONMENT=production
AWS_REGION=ap-south-1
S3_BUCKET=my-bucket
BEDROCK_IMAGE_MODEL_ID=amazon.titan-image-generator-v2:0
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
  "detected_features": ["silk texture", "gold zari", "traditional weave", "rich colors"],
  "genai_tips": "1. Source premium mulberry silk...\n2. Price at ₹1,200–₹1,500...",
  "genai_score": 78,
  "mockup_url": "https://bucket.s3.amazonaws.com/uploads/mockups/abc123.png"
}
```

---

## 🧪 Testing

```bash
cd application

# Run all tests
pytest

# Run specific test file
pytest tests/test_genai.py -v

# Coverage report
pytest --cov=src tests/
```

---

## 📁 Project Structure

```
c:\rivet_proto\
├── application/
│   ├── src/
│   │   ├── routes/           # API endpoints (analysis, admin, auth)
│   │   ├── services/         # Core logic (genai, mockup, market, cache)
│   │   ├── models/           # Database (User)
│   │   ├── config.py         # Flask config
│   │   └── app.py            # App factory
│   ├── templates/            # HTML (bilingual)
│   ├── static/               # CSS, JS, uploads
│   ├── tests/                # Pytest suite
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile            # Container image
│   └── .env.example          # Configuration template
│
├── infrastructure/           # Terraform IaC
│   ├── modules/
│   │   ├── compute/          # ECS, ALB
│   │   ├── networking/       # VPC, subnets
│   │   ├── storage/          # RDS, S3
│   │   └── secrets/          # Secrets Manager
│   ├── environments/
│   │   ├── dev/
│   │   └── prod/
│   └── README.md
│
└── README.md                 # (This file)
```

---

## 🎯 Hackathon Highlights

- **Complete End-to-End**: From sketch upload to mockup generation in one flow
- **Multi-Stage GenAI**: Draft → Critic pipeline for quality assurance
- **Real Market Data**: 1000+ product CSVs for grounded analysis
- **Production Infrastructure**: Full Terraform + Docker setup (not typical for hackathons)
- **Resilience Patterns**: Circuit breaker, caching, safety filters
- **Bilingual Support**: English + Telugu UI + **Hindi( in future)**

---

## 🚫 Known Limitations

- Local mockup generation (dev mode) is PIL-based simulation
- Market data is static CSVs (could benefit from live data integration)
- Image generation requires AWS Bedrock in production
- Admin features are minimal (proposal viewing only)

---

## 🔮 Future Enhancements

- [ ] Live market data ingestion (e.g., daily Shopify scrape)
- [ ] User behavior analytics (which tips led to successful launches?)
- [ ] A/B testing interface (test multiple design variations)
- [ ] Pricing recommendations (ML-based price optimization)
- [ ] Batch analysis (process 100 sketches per job)
- [ ] Custom rubrics by brand (e.g., "luxury" vs "budget")

---

## 📄 License

MIT License — See LICENSE file for details.

---

## 👨‍💻 Team

Built for the **AI for Bharat Hackathon** (March 2026)

**Stack**: Flask, PostgreSQL, Claude API, AWS Bedrock, Terraform, Docker

---

#   T e s t   t r i g g e r  
 