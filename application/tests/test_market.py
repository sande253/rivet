"""Tests for market_service — grounding helper and similar product finder."""
import pandas as pd
import pytest

from src.services.market_service import _find_similar, build_context


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "title": "Kanjivaram Silk Saree Gold Zari Border",
                "material_raw": "kanjivaram",
                "price_current": 1200.0,
                "price_mrp": 2500.0,
                "rating": 4.5,
                "review_count": 320.0,
                "brand": "Palam Silks",
            },
            {
                "title": "Banarasi Silk Saree Wedding Collection",
                "material_raw": "silk",
                "price_current": 1800.0,
                "price_mrp": 3500.0,
                "rating": 4.2,
                "review_count": 150.0,
                "brand": "Bunkar",
            },
            {
                "title": "Cotton Printed Casual Saree",
                "material_raw": "cotton",
                "price_current": 450.0,
                "price_mrp": 900.0,
                "rating": 3.8,
                "review_count": 80.0,
                "brand": "FabIndia",
            },
            {
                "title": "Georgette Party Wear Saree with Embroidery",
                "material_raw": "georgette",
                "price_current": 900.0,
                "price_mrp": 1800.0,
                "rating": 4.0,
                "review_count": 200.0,
                "brand": "Soch",
            },
            {
                "title": "Linen Handloom Saree Natural Dye",
                "material_raw": "linen",
                "price_current": 2200.0,
                "price_mrp": 4000.0,
                "rating": 4.7,
                "review_count": 60.0,
                "brand": "Cottonworld",
            },
        ]
    )


class TestFindSimilar:
    def test_finds_overlapping_products(self, sample_df):
        results = _find_similar("silk saree wedding", sample_df, top_n=3)
        titles = [r["title"] for r in results]
        # Banarasi Silk Saree Wedding Collection should be highly ranked
        assert any("Banarasi" in t or "Silk" in t or "Wedding" in t for t in titles)

    def test_returns_empty_for_no_overlap(self, sample_df):
        results = _find_similar("zari brocade lehenga", sample_df, top_n=5)
        # no title in sample_df contains "lehenga" or "brocade"
        assert results == []

    def test_respects_top_n_limit(self, sample_df):
        results = _find_similar("saree silk", sample_df, top_n=2)
        assert len(results) <= 2

    def test_empty_description_returns_empty(self, sample_df):
        assert _find_similar("", sample_df) == []

    def test_no_title_column_returns_empty(self):
        df = pd.DataFrame([{"brand": "X", "price_current": 800.0}])
        assert _find_similar("silk saree", df) == []


class TestBuildContext:
    def test_includes_price_band(self, sample_df):
        ctx = build_context("silk saree", "800", "saree", "Saree", sample_df)
        assert "Value" in ctx or "Mid-range" in ctx or "₹800" in ctx

    def test_budget_band_label(self, sample_df):
        ctx = build_context("cotton saree", "300", "saree", "Saree", sample_df)
        assert "Budget" in ctx

    def test_luxury_band_label(self, sample_df):
        ctx = build_context("bridal saree", "15000", "saree", "Saree", sample_df)
        assert "Luxury" in ctx

    def test_includes_market_avg(self, sample_df):
        ctx = build_context("silk saree", "1000", "saree", "Saree", sample_df)
        assert "Market avg price" in ctx

    def test_includes_similar_products(self, sample_df):
        ctx = build_context("kanjivaram silk saree", "1200", "saree", "Saree", sample_df)
        assert "Similar products" in ctx

    def test_handles_missing_price_gracefully(self, sample_df):
        ctx = build_context("saree", "", "saree", "Saree", sample_df)
        assert "not specified" in ctx or "GROUNDED CONTEXT" in ctx

    def test_handles_non_numeric_price(self, sample_df):
        ctx = build_context("saree", "abc", "saree", "Saree", sample_df)
        assert "GROUNDED CONTEXT" in ctx  # should not raise

    def test_includes_category_label(self, sample_df):
        ctx = build_context("saree", "1000", "saree", "Saree", sample_df)
        assert "SAREE" in ctx.upper()
