import os
import re

import pandas as pd
from flask import current_app

# In-process cache: avoids re-reading large CSVs on every request.
# Cleared only on process restart (acceptable for static market data).
_df_cache: dict[str, pd.DataFrame] = {}


def load_df(category: str) -> pd.DataFrame:
    """Return (and cache) the DataFrame for a given product category."""
    if category not in _df_cache:
        data_dir = current_app.config["DATA_DIR"]
        csv_filename = current_app.config["CATEGORY_CSV_MAP"][category]
        csv_path = os.path.join(data_dir, csv_filename)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file '{csv_path}' not found for category '{category}'.")

        df = pd.read_csv(csv_path)
        for col in ("price_current", "price_mrp", "rating", "review_count"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        _df_cache[category] = df

    return _df_cache[category]


def build_market_context(df: pd.DataFrame, category_label: str) -> str:
    """Build a structured market context string to inject into the Claude prompt."""
    context = [f"MARKET DATA FOR: {category_label.upper()} ({len(df)} products)"]

    if "material_raw" in df.columns:
        material_counts = df["material_raw"].value_counts().head(10)
        context.append("\n=== MARKET MATERIAL DISTRIBUTION ===")
        for mat, count in material_counts.items():
            context.append(f"  {mat}: {count} products")

    if "price_current" in df.columns:
        context.append("\n=== PRICE RANGE INSIGHTS ===")
        context.append(f"  Min price: Rs.{df['price_current'].min():.0f}")
        context.append(f"  Max price: Rs.{df['price_current'].max():.0f}")
        context.append(f"  Average price: Rs.{df['price_current'].mean():.0f}")
        context.append(f"  Median price: Rs.{df['price_current'].median():.0f}")

    if "rating" in df.columns and "review_count" in df.columns:
        top_rated = (
            df[df["rating"] >= 4.5]
            .sort_values("review_count", ascending=False)
            .head(5)
        )
        context.append("\n=== TOP PERFORMING PRODUCTS (Rating >= 4.5) ===")
        for _, row in top_rated.iterrows():
            context.append(
                f"  - {row['title']} | Rs.{row['price_current']} "
                f"| Rating: {row['rating']} | Reviews: {row['review_count']}"
            )

    if "brand" in df.columns:
        brand_counts = df["brand"].value_counts().head(8)
        context.append("\n=== TOP BRANDS BY VOLUME ===")
        for brand, count in brand_counts.items():
            context.append(f"  {brand}: {count} products")

    if "title" in df.columns:
        all_titles = " ".join(df["title"].dropna().str.lower().tolist())
        keywords = [
            "silk", "cotton", "banarasi", "kanjivaram", "zari", "handloom",
            "jacquard", "paithani", "wedding", "embroidered", "georgette",
            "linen", "rayon", "printed", "festive", "ethnic",
        ]
        context.append("\n=== KEYWORD FREQUENCY IN MARKET ===")
        for kw in keywords:
            count = all_titles.count(kw)
            if count:
                context.append(f"  '{kw}': appears {count} times")

    if "material_raw" in df.columns and "review_count" in df.columns:
        avg_reviews = (
            df.groupby("material_raw")["review_count"]
            .mean()
            .sort_values(ascending=False)
            .head(6)
        )
        context.append("\n=== AVG REVIEW COUNT BY MATERIAL (Demand Indicator) ===")
        for mat, avg in avg_reviews.items():
            context.append(f"  {mat}: {avg:.0f} avg reviews")

    return "\n".join(context)


# ---------------------------------------------------------------------------
# Grounded context — used by the Draft / Critic pipeline (GenAI layer)
# ---------------------------------------------------------------------------

def build_context(
    description: str,
    price: str,
    category: str,
    category_label: str,
    df: pd.DataFrame,
) -> str:
    """Build a grounded context string for the Draft and Critic models.

    Includes:
    - Price band classification
    - Category baseline stats (avg, median, top materials)
    - Up to 5 similar products discovered via token overlap (no vector DB)
    """
    lines = [f"GROUNDED CONTEXT: {category_label.upper()}"]

    # ── Price band ────────────────────────────────────────────────────────
    try:
        pval = float(str(price).replace(",", "").replace("₹", "").strip())
        if pval < 500:
            band = "Budget (<₹500)"
        elif pval < 1500:
            band = "Value (₹500–₹1,500)"
        elif pval < 5000:
            band = "Mid-range (₹1,500–₹5,000)"
        elif pval < 10000:
            band = "Premium (₹5,000–₹10,000)"
        else:
            band = "Luxury (₹10,000+)"
        lines.append(f"\nPrice Band: {band}  (submitted: ₹{pval:.0f})")
    except (ValueError, TypeError):
        lines.append("\nPrice Band: not specified")

    # ── Market baseline ───────────────────────────────────────────────────
    if "price_current" in df.columns:
        avg_p = df["price_current"].mean()
        med_p = df["price_current"].median()
        lines.append(f"Market avg price: ₹{avg_p:.0f}  |  Median: ₹{med_p:.0f}")

    if "material_raw" in df.columns:
        top_mats = df["material_raw"].value_counts().head(3)
        lines.append(
            "Top materials: " + ", ".join(f"{m}({c})" for m, c in top_mats.items())
        )

    # ── Similar products (token-overlap RAG-lite) ─────────────────────────
    similar = _find_similar(description, df, top_n=5)
    if similar:
        lines.append("\nSimilar products in dataset:")
        for row in similar:
            title = str(row.get("title", ""))[:60]
            price_s = row.get("price_current", "?")
            rating = row.get("rating", "?")
            try:
                price_s = f"₹{float(price_s):.0f}"
            except (ValueError, TypeError):
                price_s = "₹?"
            lines.append(f"  - {title} | {price_s} | ★{rating}")

    return "\n".join(lines)


def _find_similar(description: str, df: pd.DataFrame, top_n: int = 5) -> list[dict]:
    """Return top-N similar products by token overlap with description."""
    if "title" not in df.columns or not description:
        return []
    desc_tokens = set(re.split(r"\W+", description.lower()))
    desc_tokens.discard("")
    scored: list[tuple[int, dict]] = []
    for _, row in df.iterrows():
        title_tokens = set(re.split(r"\W+", str(row.get("title", "")).lower()))
        overlap = len(desc_tokens & title_tokens)
        if overlap > 0:
            scored.append((overlap, row.to_dict()))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_n]]
