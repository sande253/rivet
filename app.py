import os
import base64
import json
import pandas as pd
import anthropic
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

# ─── Only these two lines changed/added ───
from dotenv import load_dotenv
load_dotenv()
# ───────────────────────────────────────────

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Load and preprocess saree data
df = pd.read_csv('clean_saree_data.csv')

# ... rest of your code remains 100% unchanged ..

# Build market context from the dataset
def build_market_context():
    """Summarize the dataset into market insights for the AI."""
    context = []

    # Material distribution
    material_counts = df['material_raw'].value_counts().head(10)
    context.append("=== MARKET MATERIAL DISTRIBUTION ===")
    for mat, count in material_counts.items():
        context.append(f"  {mat}: {count} products")

    # Price ranges
    context.append("\n=== PRICE RANGE INSIGHTS ===")
    context.append(f"  Min price: ₹{df['price_current'].min():.0f}")
    context.append(f"  Max price: ₹{df['price_current'].max():.0f}")
    context.append(f"  Average price: ₹{df['price_current'].mean():.0f}")
    context.append(f"  Median price: ₹{df['price_current'].median():.0f}")

    # Top rated products
    top_rated = df[df['rating'] >= 4.5].sort_values('review_count', ascending=False).head(5)
    context.append("\n=== TOP PERFORMING PRODUCTS (Rating ≥ 4.5) ===")
    for _, row in top_rated.iterrows():
        context.append(f"  • {row['title']} | ₹{row['price_current']} | Rating: {row['rating']} | Reviews: {row['review_count']}")

    # Popular brands
    brand_counts = df['brand'].value_counts().head(8)
    context.append("\n=== TOP BRANDS BY VOLUME ===")
    for brand, count in brand_counts.items():
        context.append(f"  {brand}: {count} products")

    # Common keywords from titles
    all_titles = ' '.join(df['title'].dropna().str.lower().tolist())
    keywords = ['silk', 'cotton', 'banarasi', 'kanjivaram', 'zari', 'handloom', 'jacquard',
                'paithani', 'wedding', 'blouse', 'printed', 'embroidered', 'georgette', 'linen']
    context.append("\n=== KEYWORD FREQUENCY IN MARKET ===")
    for kw in keywords:
        count = all_titles.count(kw)
        context.append(f"  '{kw}': appears {count} times")

    # Average review counts by material
    avg_reviews = df.groupby('material_raw')['review_count'].mean().sort_values(ascending=False).head(6)
    context.append("\n=== AVG REVIEW COUNT BY MATERIAL (Demand Indicator) ===")
    for mat, avg in avg_reviews.items():
        context.append(f"  {mat}: {avg:.0f} avg reviews")

    return '\n'.join(context)

MARKET_CONTEXT = build_market_context()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_sketch_with_claude(image_path, image_mime_type):
    """Send sketch to Claude API for semantic analysis."""
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    system_prompt = f"""You are an expert saree product analyst and fashion market researcher.
You have deep knowledge of the Indian saree market with access to real market data.

REAL MARKET DATA FROM 578 SAREE PRODUCTS:
{MARKET_CONTEXT}

Your task is to analyze a sketch/image of a saree product and provide:
1. A detailed semantic analysis of the design
2. Market viability scoring across multiple dimensions
3. A final classification decision

SCORING CRITERIA (each out of 20, total out of 100):
1. **Market Demand Score** (0-20): How much demand exists for this style/material based on market data?
   - High review counts in similar products = higher score
   - Trending materials/styles = higher score

2. **Design Uniqueness Score** (0-20): How differentiated is this product?
   - Overcrowded market segment = lower score
   - Unique design elements = higher score

3. **Price Competitiveness Score** (0-20): Estimated price point vs market?
   - Premium but justified = higher score
   - Overpriced for segment = lower score

4. **Material Appeal Score** (0-20): Quality/desirability of material visible?
   - Silk/handloom = higher premium potential
   - Synthetic blends = lower score

5. **Trend Alignment Score** (0-20): How well does it align with current trends?
   - Wedding/festive wear trending = bonus
   - Everyday cotton growing = bonus

CLASSIFICATION RULES:
- Score 75-100: **LAUNCH** ✅ (Strong market fit, proceed to production)
- Score 50-74: **MODIFY** ⚠️ (Promising but needs adjustments before launch)
- Score 0-49: **DO NOT PRODUCE** ❌ (Poor market fit, high risk)

Respond ONLY with a valid JSON object in this exact format:
{{
  "design_description": "Detailed description of what you see in the sketch (2-3 sentences)",
  "detected_style": "e.g., Kanjivaram Silk / Banarasi / Cotton Handloom / etc.",
  "detected_features": ["feature1", "feature2", "feature3"],
  "scores": {{
    "market_demand": <0-20>,
    "design_uniqueness": <0-20>,
    "price_competitiveness": <0-20>,
    "material_appeal": <0-20>,
    "trend_alignment": <0-20>
  }},
  "total_score": <0-100>,
  "classification": "LAUNCH" | "MODIFY" | "DO NOT PRODUCE",
  "classification_reasoning": "2-3 sentence explanation of why this classification was given",
  "market_insights": "Key market insight relevant to this product (1-2 sentences)",
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
  "similar_top_products": ["brief description of 1-2 similar successful products from the dataset"]
}}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_mime_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Please analyze this saree product sketch/design and provide the full JSON analysis."
                    }
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    # Clean potential markdown code fences
    if raw_text.startswith('```'):
        raw_text = raw_text.split('```')[1]
        if raw_text.startswith('json'):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    return json.loads(raw_text)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'sketch' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['sketch']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Determine MIME type
    ext = filename.rsplit('.', 1)[1].lower()
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'webp': 'image/webp'}
    mime_type = mime_map.get(ext, 'image/jpeg')

    try:
        result = analyze_sketch_with_claude(filepath, mime_type)
        result['image_url'] = f'/static/uploads/{filename}'
        return jsonify(result)
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse AI response: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/market-summary')
def market_summary():
    """Return a quick summary of the dataset."""
    summary = {
        'total_products': len(df),
        'avg_price': round(df['price_current'].mean(), 2),
        'top_materials': df['material_raw'].value_counts().head(5).to_dict(),
        'top_brands': df['brand'].value_counts().head(5).to_dict(),
        'avg_rating': round(df['rating'].mean(), 2),
    }
    return jsonify(summary)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print("🚀 Saree Analyzer running on http://localhost:5000")
    print("⚠️  Make sure ANTHROPIC_API_KEY environment variable is set!")
    app.run(debug=True, port=5000)
