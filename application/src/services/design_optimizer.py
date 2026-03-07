"""AI Design Optimizer service.

Generates actionable improvement suggestions with quantified impact.
Shows users exactly what to change to improve their product score.
"""

from __future__ import annotations

import logging
from typing import TypedDict

log = logging.getLogger(__name__)


class OptimizationSuggestion(TypedDict):
    """Single optimization suggestion structure."""
    id: str
    title: str
    description: str
    impact_points: int
    new_score: int
    new_classification: str
    cost_impact: str
    demand_impact: str
    priority: str  # high, medium, low
    change_type: str  # material, price, description, occasion


class OptimizationResult(TypedDict):
    """Complete optimization result structure."""
    current_score: int
    current_classification: str
    suggestions: list[OptimizationSuggestion]
    best_combination: dict
    can_reach_proceed: bool


# Material upgrade mappings with score impact
MATERIAL_UPGRADES = {
    "polyester": {"upgrade": "Cotton Blend", "points": 8, "cost": 150},
    "synthetic": {"upgrade": "Cotton", "points": 10, "cost": 200},
    "rayon": {"upgrade": "Silk Blend", "points": 12, "cost": 300},
    "cotton": {"upgrade": "Pure Silk", "points": 15, "cost": 500},
    "cotton blend": {"upgrade": "Handloom Cotton", "points": 10, "cost": 250},
}

# Price optimization ranges by category
PRICE_SWEET_SPOTS = {
    "saree": {"min": 800, "max": 1500, "optimal": 1200},
    "lehenga": {"min": 1500, "max": 3000, "optimal": 2200},
    "salwar_suit": {"min": 600, "max": 1200, "optimal": 900},
    "kurti": {"min": 400, "max": 800, "optimal": 600},
    "kurta": {"min": 500, "max": 1000, "optimal": 750},
    "kurta_pyjama": {"min": 800, "max": 1500, "optimal": 1100},
    "sherwani": {"min": 2000, "max": 5000, "optimal": 3500},
}

# High-value occasions that boost demand
PREMIUM_OCCASIONS = {
    "wedding": {"points": 5, "demand_boost": 20},
    "festival": {"points": 4, "demand_boost": 15},
    "party": {"points": 3, "demand_boost": 10},
    "formal": {"points": 2, "demand_boost": 5},
}


def generate_optimizations(
    category: str,
    price: float,
    total_score: int,
    scores: dict,
    description: str,
    occasion: str,
    material: str,
    classification: str,
) -> OptimizationResult:
    """
    Generate actionable optimization suggestions.
    
    Args:
        category: Product category
        price: Current price
        total_score: Current total score
        scores: Individual dimension scores
        description: Product description
        occasion: Current occasion
        material: Current material
        classification: Current classification
    
    Returns:
        OptimizationResult with suggestions and best combination
    """
    suggestions = []
    
    # 1. Material optimization
    material_lower = material.lower()
    for mat_key, upgrade_info in MATERIAL_UPGRADES.items():
        if mat_key in material_lower:
            new_score = total_score + upgrade_info["points"]
            new_class = _get_classification(new_score)
            
            suggestions.append({
                "id": "material_upgrade",
                "title": f"Upgrade material to {upgrade_info['upgrade']}",
                "description": f"Switch from {material} to {upgrade_info['upgrade']} for better material appeal",
                "impact_points": upgrade_info["points"],
                "new_score": new_score,
                "new_classification": new_class,
                "cost_impact": f"+₹{upgrade_info['cost']} per unit",
                "demand_impact": f"+{int(upgrade_info['points'] * 0.5)} units/month",
                "priority": "high" if upgrade_info["points"] >= 10 else "medium",
                "change_type": "material",
            })
            break
    
    # 2. Price optimization
    if category in PRICE_SWEET_SPOTS:
        sweet_spot = PRICE_SWEET_SPOTS[category]
        if price < sweet_spot["min"] or price > sweet_spot["max"]:
            optimal_price = sweet_spot["optimal"]
            price_diff = optimal_price - price
            
            # Price impact on score
            if price > sweet_spot["max"]:
                points = 10  # Too expensive
                demand_change = -15
            elif price < sweet_spot["min"]:
                points = 8  # Too cheap (perceived low quality)
                demand_change = 5
            else:
                points = 5
                demand_change = 10
            
            new_score = total_score + points
            new_class = _get_classification(new_score)
            
            action = "Reduce" if price_diff < 0 else "Increase"
            suggestions.append({
                "id": "price_optimize",
                "title": f"{action} price to ₹{optimal_price}",
                "description": f"Optimal price point for {category} category based on market data",
                "impact_points": points,
                "new_score": new_score,
                "new_classification": new_class,
                "cost_impact": f"{price_diff:+.0f} per unit",
                "demand_impact": f"{demand_change:+d} units/month",
                "priority": "high" if abs(price_diff) > 300 else "medium",
                "change_type": "price",
            })
    
    # 3. Occasion optimization
    occasion_lower = occasion.lower()
    for premium_occ, occ_info in PREMIUM_OCCASIONS.items():
        if premium_occ not in occasion_lower and premium_occ not in description.lower():
            new_score = total_score + occ_info["points"]
            new_class = _get_classification(new_score)
            
            suggestions.append({
                "id": f"occasion_{premium_occ}",
                "title": f"Target {premium_occ.title()} market",
                "description": f"Add '{premium_occ.title()} Collection' to description to target high-value occasions",
                "impact_points": occ_info["points"],
                "new_score": new_score,
                "new_classification": new_class,
                "cost_impact": "No cost change",
                "demand_impact": f"+{occ_info['demand_boost']} units/month",
                "priority": "medium",
                "change_type": "occasion",
            })
            break  # Only suggest one occasion change
    
    # 4. Design uniqueness boost
    if scores.get("design_uniqueness", 0) < 15:
        points = 6
        new_score = total_score + points
        new_class = _get_classification(new_score)
        
        suggestions.append({
            "id": "design_unique",
            "title": "Add unique design elements",
            "description": "Incorporate distinctive patterns, embroidery, or color combinations to stand out",
            "impact_points": points,
            "new_score": new_score,
            "new_classification": new_class,
            "cost_impact": "+₹100-200 per unit",
            "demand_impact": "+8 units/month",
            "priority": "medium",
            "change_type": "description",
        })
    
    # 5. Trend alignment boost
    if scores.get("trend_alignment", 0) < 15:
        points = 5
        new_score = total_score + points
        new_class = _get_classification(new_score)
        
        suggestions.append({
            "id": "trend_align",
            "title": "Align with current trends",
            "description": "Add trending colors (pastels, earth tones) or contemporary design elements",
            "impact_points": points,
            "new_score": new_score,
            "new_classification": new_class,
            "cost_impact": "Minimal",
            "demand_impact": "+10 units/month",
            "priority": "low",
            "change_type": "description",
        })
    
    # Sort by priority and impact
    suggestions.sort(key=lambda x: (
        {"high": 3, "medium": 2, "low": 1}[x["priority"]],
        x["impact_points"]
    ), reverse=True)
    
    # Calculate best combination (top 2-3 suggestions)
    best_combo = _calculate_best_combination(suggestions[:3], total_score)
    
    # Check if can reach PROCEED
    can_reach_proceed = best_combo["new_score"] >= 75
    
    return {
        "current_score": total_score,
        "current_classification": classification,
        "suggestions": suggestions[:5],  # Top 5 suggestions
        "best_combination": best_combo,
        "can_reach_proceed": can_reach_proceed,
    }


def _get_classification(score: int) -> str:
    """Get classification from score."""
    if score >= 75:
        return "PROCEED"
    elif score >= 50:
        return "MODIFY"
    else:
        return "RECONSIDER"


def _calculate_best_combination(suggestions: list, current_score: int) -> dict:
    """Calculate the best combination of suggestions."""
    if not suggestions:
        return {
            "changes": [],
            "total_impact": 0,
            "new_score": current_score,
            "new_classification": _get_classification(current_score),
            "total_cost_impact": "No changes",
            "total_demand_impact": "No change",
        }
    
    total_points = sum(s["impact_points"] for s in suggestions)
    new_score = min(current_score + total_points, 100)  # Cap at 100
    
    # Aggregate cost and demand impacts
    cost_impacts = []
    demand_impacts = []
    
    for s in suggestions:
        if "₹" in s["cost_impact"]:
            cost_impacts.append(s["cost_impact"])
        if "units" in s["demand_impact"]:
            try:
                units = int(s["demand_impact"].split()[0].replace("+", ""))
                demand_impacts.append(units)
            except:
                pass
    
    total_cost = " + ".join(cost_impacts) if cost_impacts else "Minimal"
    total_demand = f"+{sum(demand_impacts)} units/month" if demand_impacts else "+15 units/month"
    
    return {
        "changes": [s["title"] for s in suggestions],
        "total_impact": total_points,
        "new_score": new_score,
        "new_classification": _get_classification(new_score),
        "total_cost_impact": total_cost,
        "total_demand_impact": total_demand,
    }
