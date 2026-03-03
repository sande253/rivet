import base64
import json
import os

from flask import current_app

from .market_service import load_df, build_market_context

# Use Bedrock client instead of Anthropic SDK
USE_BEDROCK = os.environ.get("USE_BEDROCK", "true").lower() in ("1", "true", "yes")

if USE_BEDROCK:
    from .bedrock_client import BedrockClient as AnthropicClient
else:
    import anthropic
    AnthropicClient = anthropic.Anthropic


def analyze_sketch_with_claude(image_path: str, image_mime_type: str, category: str) -> dict:
    """Send the uploaded product image to Claude with market context and return structured JSON."""
    category_labels = current_app.config["CATEGORY_LABELS"]

    # Initialize client (Bedrock uses IAM role, Anthropic uses API key)
    if USE_BEDROCK:
        client = AnthropicClient()
    else:
        api_key = current_app.config["ANTHROPIC_API_KEY"]
        client = AnthropicClient(api_key=api_key)

    df = load_df(category)
    category_label = category_labels[category]
    market_context = build_market_context(df, category_label)
    total_products = len(df)

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    system_prompt = f"""You are an experienced product development consultant specializing in Indian ethnic wear, with a focus on helping designers bring their creative visions to market successfully.

YOUR ROLE: Evaluate product sketches and designs to provide constructive, actionable guidance that helps clients refine and launch their products. You understand that sketches are early-stage concepts meant to capture design intent, not final production samples.

MARKET INTELLIGENCE - {category_label.upper()} CATEGORY:
{market_context}

Based on analysis of {total_products} products currently in the market.

EVALUATION APPROACH:
- Treat the image as a DESIGN CONCEPT that shows the client's creative vision
- Focus on the DESIGN ELEMENTS visible (patterns, borders, colors, style)
- Provide CONSTRUCTIVE feedback that helps improve market fit
- Avoid dismissing concepts as "just sketches" - evaluate the design merit
- Use business-friendly language (avoid technical terms like "dataset", "data points", etc.)

SCORING FRAMEWORK (each dimension 0-20, total 0-100):
1. market_demand: How well this design style aligns with current customer preferences
2. design_uniqueness: Distinctive elements that differentiate from competitors
3. price_competitiveness: Potential to price competitively based on design complexity
4. material_appeal: Design elements that suggest quality and craftsmanship
5. trend_alignment: Alignment with current fashion trends and customer preferences

CLASSIFICATION GUIDANCE:
- 75-100: LAUNCH - Strong design with clear market potential
- 50-74: MODIFY - Good foundation, specific improvements recommended
- 0-49: DO NOT PRODUCE - Significant market fit concerns

IMPORTANT GUIDELINES:
- Focus on what you CAN see in the design (patterns, style, borders, colors)
- Provide specific, actionable recommendations
- Be encouraging while being honest about market realities
- Never use words like: dataset, data points, database, training data, model
- Use business terms: market research, customer preferences, industry trends, market analysis

Respond ONLY with this exact JSON structure - no markdown, no extra text:
{{
  "category": "{category_label}",
  "design_description": "Clear 2-sentence description focusing on the design elements, style, and aesthetic appeal.",
  "detected_style": "e.g. Traditional Border Design / Contemporary Print / Embroidered {category_label}",
  "detected_features": ["feature1", "feature2", "feature3", "feature4"],
  "scores": {{
    "market_demand": <integer 0-20>,
    "design_uniqueness": <integer 0-20>,
    "price_competitiveness": <integer 0-20>,
    "material_appeal": <integer 0-20>,
    "trend_alignment": <integer 0-20>
  }},
  "total_score": <integer 0-100>,
  "classification": "LAUNCH" or "MODIFY" or "DO NOT PRODUCE",
  "classification_reasoning": "2-sentence explanation focusing on design strengths and market opportunities.",
  "market_insights": "1-sentence insight about how this design fits current market trends.",
  "market_points": [
    "Competition: How this design compares to current offerings",
    "Pricing: Estimated price range based on design complexity",
    "Demand: Customer interest in this style category",
    "Appeal: Target customer segment and preferences",
    "Opportunity: Market gaps this design could fill"
  ],
  "data_insights": [
    "Similar styles currently popular in the market",
    "Typical price range for this design category",
    "Customer ratings for similar styles",
    "Positive customer feedback themes",
    "Common improvement suggestions from customers"
  ],
  "recommendations": [
    "Specific design enhancement with expected market impact",
    "Material or finish suggestion with customer appeal benefit",
    "Pricing or positioning strategy with competitive advantage"
  ]
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
                        "text": f"Please evaluate this {category_label} design concept and provide constructive guidance to help bring it to market successfully. Focus on the design elements, style, and market potential.",
                    },
                ],
            }
        ],
    )

    raw_text = response.content[0].text.strip()
    # Strip markdown code fences if the model wraps its response
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    return json.loads(raw_text)
