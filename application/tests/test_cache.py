"""Tests for cache_service — key normalisation, TTL, get/set."""
import time

import pytest

from src.services.cache_service import (
    cache_clear,
    cache_get,
    cache_set,
    make_analysis_key,
)


@pytest.fixture(autouse=True)
def clear_cache():
    cache_clear()
    yield
    cache_clear()


class TestMakeAnalysisKey:
    def test_same_inputs_produce_same_key(self):
        k1 = make_analysis_key("silk saree", "800", "saree")
        k2 = make_analysis_key("silk saree", "800", "saree")
        assert k1 == k2

    def test_case_insensitive_normalisation(self):
        k1 = make_analysis_key("Silk Saree", "800", "Saree")
        k2 = make_analysis_key("silk saree", "800", "saree")
        assert k1 == k2

    def test_whitespace_normalisation(self):
        k1 = make_analysis_key("  silk saree  ", " 800 ", " saree ")
        k2 = make_analysis_key("silk saree", "800", "saree")
        assert k1 == k2

    def test_different_prices_produce_different_keys(self):
        k1 = make_analysis_key("silk saree", "800", "saree")
        k2 = make_analysis_key("silk saree", "1200", "saree")
        assert k1 != k2

    def test_different_categories_produce_different_keys(self):
        k1 = make_analysis_key("silk saree", "800", "saree")
        k2 = make_analysis_key("silk saree", "800", "lehenga")
        assert k1 != k2

    def test_subcategory_included_in_key(self):
        k1 = make_analysis_key("saree", "800", "saree", "kanjivaram")
        k2 = make_analysis_key("saree", "800", "saree", "banarasi")
        assert k1 != k2


class TestCacheGetSet:
    def test_set_and_get_returns_value(self):
        cache_set("key1", {"genai_tips": "tip text"}, ttl=60)
        result = cache_get("key1")
        assert result == {"genai_tips": "tip text"}

    def test_missing_key_returns_none(self):
        assert cache_get("does-not-exist") is None

    def test_expired_entry_returns_none(self):
        cache_set("key2", "value", ttl=1)
        time.sleep(1.1)
        assert cache_get("key2") is None

    def test_non_expired_entry_is_returned(self):
        cache_set("key3", "persistent", ttl=60)
        assert cache_get("key3") == "persistent"

    def test_overwrite_existing_key(self):
        cache_set("key4", "v1", ttl=60)
        cache_set("key4", "v2", ttl=60)
        assert cache_get("key4") == "v2"

    def test_cache_clear_removes_all(self):
        cache_set("a", 1)
        cache_set("b", 2)
        cache_clear()
        assert cache_get("a") is None
        assert cache_get("b") is None
