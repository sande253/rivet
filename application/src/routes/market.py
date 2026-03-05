import logging

import pandas as pd
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required

from ..services.market_service import load_df

market_bp = Blueprint("market", __name__)
log = logging.getLogger(__name__)


@market_bp.route("/categories")
@login_required
def categories():
    labels = current_app.config["CATEGORY_LABELS"]
    return jsonify({"categories": [{"id": k, "label": v} for k, v in labels.items()]})


@market_bp.route("/market-summary")
@login_required
def market_summary():
    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    category_labels = current_app.config["CATEGORY_LABELS"]
    category = request.args.get("category", "saree").strip().lower()

    if category not in category_csv_map:
        return jsonify({"error": f"Unknown category. Valid options: {', '.join(category_csv_map.keys())}"}), 400

    try:
        df = load_df(category)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "category":       category_labels[category],
        "total_products": len(df),
        "avg_price":      round(df["price_current"].mean(), 2) if "price_current" in df.columns else None,
        "top_materials":  df["material_raw"].value_counts().head(5).to_dict() if "material_raw" in df.columns else {},
        "top_brands":     df["brand"].value_counts().head(5).to_dict() if "brand" in df.columns else {},
        "avg_rating":     round(df["rating"].mean(), 2) if "rating" in df.columns else None,
    })


@market_bp.route("/market-insights")
@login_required
def market_insights():
    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    category_labels = current_app.config["CATEGORY_LABELS"]
    category = request.args.get("category", "saree").strip().lower()

    if category not in category_csv_map:
        return jsonify({"error": f"Unknown category. Valid options: {', '.join(category_csv_map.keys())}"}), 400

    try:
        df = load_df(category)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    insights = {
        "category":       category_labels[category],
        "total_products": len(df),
        "avg_price":      round(df["price_current"].mean(), 2) if "price_current" in df.columns else 0,
        "avg_rating":     round(df["rating"].mean(), 2) if "rating" in df.columns else 0,
    }

    if "rating" in df.columns:
        insights["high_demand_pct"] = round(len(df[df["rating"] >= 4.0]) / len(df) * 100, 0)
    else:
        insights["high_demand_pct"] = 0

    if "material_raw" in df.columns:
        material_counts = df["material_raw"].value_counts().head(4)
        insights["materials"] = [
            {"name": mat, "count": int(count)} for mat, count in material_counts.items()
        ]
    else:
        insights["materials"] = []

    if "price_current" in df.columns:
        price_ranges = [
            ("Under ₹2,000",      df[df["price_current"] < 2000]),
            ("₹2,000 - ₹5,000",   df[(df["price_current"] >= 2000) & (df["price_current"] < 5000)]),
            ("₹5,000 - ₹10,000",  df[(df["price_current"] >= 5000) & (df["price_current"] < 10000)]),
            ("Above ₹10,000",     df[df["price_current"] >= 10000]),
        ]
        insights["price_distribution"] = [
            {"range": label, "percentage": round(len(subset) / len(df) * 100, 0)}
            for label, subset in price_ranges
        ]
    else:
        insights["price_distribution"] = []

    required_cols = {"title", "rating", "review_count", "price_current"}
    if required_cols.issubset(df.columns):
        top_products = (
            df[df["rating"] >= 4.0]
            .sort_values("review_count", ascending=False)
            .head(6)
        )
        insights["top_products"] = [
            {
                "title":    row["title"][:50] + ("..." if len(row["title"]) > 50 else ""),
                "rating":   round(row["rating"], 1),
                "reviews":  int(row["review_count"]),
                "price":    round(row["price_current"], 0),
                "material": row.get("material_raw", "N/A"),
            }
            for _, row in top_products.iterrows()
        ]
    else:
        insights["top_products"] = []

    return jsonify(insights)


@market_bp.route("/products")
@login_required
def products():
    """Return product listings from CSV files for the market table."""
    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    category_labels = current_app.config["CATEGORY_LABELS"]
    
    # Get all products from all categories
    all_products = []
    
    for cat_id, csv_file in category_csv_map.items():
        try:
            df = load_df(cat_id)
            
            # Required columns check
            required_cols = {"title", "brand", "price_current", "price_mrp", "rating", "review_count"}
            if not required_cols.issubset(df.columns):
                log.warning(f"Category {cat_id} missing required columns")
                continue
            
            # Convert to list of dicts
            for _, row in df.iterrows():
                try:
                    product = {
                        "title": str(row["title"])[:80],
                        "brand": str(row.get("brand", "Unknown")),
                        "cat": cat_id,
                        "price": int(row["price_current"]) if pd.notna(row["price_current"]) else 0,
                        "mrp": int(row["price_mrp"]) if pd.notna(row["price_mrp"]) else 0,
                        "rating": round(float(row["rating"]), 1) if pd.notna(row["rating"]) else 0,
                        "reviews": int(row["review_count"]) if pd.notna(row["review_count"]) else 0,
                    }
                    all_products.append(product)
                except (ValueError, TypeError) as e:
                    log.debug(f"Skipping row due to data error: {e}")
                    continue
                    
        except Exception as e:
            log.error(f"Error loading products from {cat_id}: {e}")
            continue
    
    return jsonify({
        "products": all_products,
        "total": len(all_products),
        "categories": category_labels
    })

