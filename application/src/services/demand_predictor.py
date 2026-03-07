"""Demand prediction service.

Predicts first-month sales volume based on:
- Market data analysis
- Price positioning
- Competition density
- Product uniqueness score
- Category baseline demand
"""

from __future__ import annotations

import logging
import os
from typing import TypedDict

log = logging.getLogger(__name__)


class DemandPrediction(TypedDict):
    """Demand prediction result structure."""
    units_min: int
    units_max: int
    units_estimate: int
    revenue_min: int
    revenue_max: int
    revenue_estimate: int
    confidence: int
    confidence_label: str
    factors: dict
    insights: list[str]
    recommendations: list[str]


# Category baseline monthly sales (conservative estimates)
CATEGORY_BASE_DEMAND = {
    "saree": 60,
    "lehenga": 35,
    "salwar_suit": 55,
    "kurti": 70,
    "kurta": 45,
    "kurta_pyjama": 40,
    "sherwani": 25,
}


def predict_demand(
    category: str,
    price: float,
    total_score: int,
    scores: dict,
    market_data: list[dict],
) -> DemandPrediction:
    """
    Predict first-month sales demand for a product.
    
    Args:
        category: Product category (saree, lehenga, etc.)
        price: Target selling price
        total_score: Overall product score (0-100)
        scores: Individual dimension scores
        market_data: List of competitor products
    
    Returns:
        DemandPrediction with sales estimates and insights
    """
    # Base demand from category
    base_demand = CATEGORY_BASE_DEMAND.get(category, 50)
    
    # Calculate factors
    price_factor = _calculate_price_factor(price, market_data)
    competition_factor = _calculate_competition_factor(category, market_data)
    uniqueness_factor = _calculate_uniqueness_factor(scores)
    score_factor = _calculate_score_factor(total_score)
    
    # Combined multiplier
    total_multiplier = price_factor * competition_factor * uniqueness_factor * score_factor
    
    # Predicted units
    units_estimate = int(base_demand * total_multiplier)
    units_min = int(units_estimate * 0.75)  # -25% variance
    units_max = int(units_estimate * 1.35)  # +35% variance
    
    # Revenue projections
    revenue_estimate = int(units_estimate * price)
    revenue_min = int(units_min * price)
    revenue_max = int(units_max * price)
    
    # Confidence calculation
    confidence = _calculate_confidence(market_data, total_score)
    confidence_label = _get_confidence_label(confidence)
    
    # Generate insights
    insights = _generate_insights(
        category, price, market_data, price_factor, 
        competition_factor, uniqueness_factor, total_score
    )
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        units_estimate, price, price_factor, competition_factor, 
        uniqueness_factor, total_score
    )
    
    return {
        "units_min": units_min,
        "units_max": units_max,
        "units_estimate": units_estimate,
        "revenue_min": revenue_min,
        "revenue_max": revenue_max,
        "revenue_estimate": revenue_estimate,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "factors": {
            "base_demand": base_demand,
            "price_factor": round(price_factor, 2),
            "competition_factor": round(competition_factor, 2),
            "uniqueness_factor": round(uniqueness_factor, 2),
            "score_factor": round(score_factor, 2),
            "total_multiplier": round(total_multiplier, 2),
        },
        "insights": insights,
        "recommendations": recommendations,
    }


def _calculate_price_factor(price: float, market_data: list[dict]) -> float:
    """Calculate demand adjustment based on price positioning."""
    if not market_data:
        return 1.0
    
    prices = [p.get("price", 0) for p in market_data if p.get("price", 0) > 0]
    if not prices:
        return 1.0
    
    avg_price = sum(prices) / len(prices)
    
    if price < avg_price * 0.7:
        return 1.25  # Very cheap - high demand boost
    elif price < avg_price * 0.9:
        return 1.15  # Below average - good demand
    elif price < avg_price * 1.1:
        return 1.0   # Average pricing
    elif price < avg_price * 1.3:
        return 0.85  # Above average - reduced demand
    else:
        return 0.65  # Premium pricing - niche demand


def _calculate_competition_factor(category: str, market_data: list[dict]) -> float:
    """Calculate demand adjustment based on competition density."""
    if not market_data:
        return 1.0
    
    # Count competitors in same category
    competitors = len([p for p in market_data if p.get("cat") == category])
    
    if competitors < 50:
        return 1.2   # Low competition - opportunity
    elif competitors < 150:
        return 1.0   # Moderate competition
    elif competitors < 300:
        return 0.85  # High competition
    else:
        return 0.7   # Very saturated market


def _calculate_uniqueness_factor(scores: dict) -> float:
    """Calculate demand boost from design uniqueness."""
    uniqueness_score = scores.get("design_uniqueness", 10)
    
    if uniqueness_score >= 18:
        return 1.3   # Highly unique - strong differentiator
    elif uniqueness_score >= 15:
        return 1.15  # Good uniqueness
    elif uniqueness_score >= 12:
        return 1.0   # Average
    else:
        return 0.9   # Low uniqueness


def _calculate_score_factor(total_score: int) -> float:
    """Calculate demand adjustment based on overall product score."""
    if total_score >= 85:
        return 1.25  # Excellent product
    elif total_score >= 75:
        return 1.1   # Strong product
    elif total_score >= 60:
        return 1.0   # Good product
    elif total_score >= 50:
        return 0.85  # Needs improvement
    else:
        return 0.7   # Weak product


def _calculate_confidence(market_data: list[dict], total_score: int) -> int:
    """Calculate prediction confidence score (0-100)."""
    confidence = 50  # Base confidence
    
    # More market data = higher confidence
    if len(market_data) > 200:
        confidence += 20
    elif len(market_data) > 100:
        confidence += 15
    elif len(market_data) > 50:
        confidence += 10
    
    # Higher product score = more predictable
    if total_score >= 75:
        confidence += 15
    elif total_score >= 60:
        confidence += 10
    elif total_score >= 50:
        confidence += 5
    
    # Cap at 95 (never 100% certain)
    return min(confidence, 95)


def _get_confidence_label(confidence: int) -> str:
    """Convert confidence score to label."""
    if confidence >= 80:
        return "High"
    elif confidence >= 60:
        return "Medium"
    else:
        return "Low"


def _generate_insights(
    category: str,
    price: float,
    market_data: list[dict],
    price_factor: float,
    competition_factor: float,
    uniqueness_factor: float,
    total_score: int,
) -> list[str]:
    """Generate actionable insights about the prediction."""
    insights = []
    
    # Competition insight
    competitors = len([p for p in market_data if p.get("cat") == category])
    insights.append(f"{competitors} similar products in market")
    
    # Price positioning
    if market_data:
        prices = [p.get("price", 0) for p in market_data if p.get("price", 0) > 0]
        if prices:
            avg_price = sum(prices) / len(prices)
            diff_pct = int(((price - avg_price) / avg_price) * 100)
            if diff_pct < -10:
                insights.append(f"Your price is {abs(diff_pct)}% below average (competitive)")
            elif diff_pct > 10:
                insights.append(f"Your price is {diff_pct}% above average (premium)")
            else:
                insights.append("Your price matches market average")
    
    # Uniqueness insight
    if uniqueness_factor >= 1.15:
        insights.append("Strong design differentiation (competitive advantage)")
    elif uniqueness_factor < 0.95:
        insights.append("Low design uniqueness (may struggle to stand out)")
    
    # Score insight
    if total_score >= 75:
        insights.append("High product score indicates strong market fit")
    elif total_score < 60:
        insights.append("Product score suggests improvements needed")
    
    return insights


def _generate_recommendations(
    units_estimate: int,
    price: float,
    price_factor: float,
    competition_factor: float,
    uniqueness_factor: float,
    total_score: int,
) -> list[str]:
    """Generate actionable recommendations."""
    recommendations = []
    
    # Initial production recommendation
    if units_estimate < 30:
        recommendations.append("Start with 20-30 units to test market response")
    elif units_estimate < 60:
        recommendations.append(f"Launch with {int(units_estimate * 0.8)}-{units_estimate} units")
    else:
        recommendations.append(f"Strong demand predicted - consider {units_estimate} units for first batch")
    
    # Pricing recommendations
    if price_factor > 1.15:
        recommendations.append(f"Consider increasing price by ₹{int(price * 0.1)}-₹{int(price * 0.2)} to improve margins")
    elif price_factor < 0.85:
        recommendations.append("Premium pricing may limit volume - ensure quality justifies cost")
    
    # Competition recommendations
    if competition_factor < 0.85:
        recommendations.append("High competition - focus marketing on unique features")
    
    # Uniqueness recommendations
    if uniqueness_factor < 1.0:
        recommendations.append("Enhance design uniqueness to stand out from competitors")
    
    # Score-based recommendations
    if total_score < 60:
        recommendations.append("Improve product score before launch to increase success probability")
    
    return recommendations
