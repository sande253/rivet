"""Tests for safety.py — pre-flight and post-flight checks."""
import pytest

from src.services.safety import post_flight_clean, pre_flight_check


class TestPreFlightCheck:
    def test_empty_string_is_ok(self):
        ok, reason = pre_flight_check("")
        assert ok is True
        assert reason == ""

    def test_clean_text_passes(self):
        ok, reason = pre_flight_check("Cotton saree with zari border, targeting ₹800 price.")
        assert ok is True

    def test_profanity_blocked(self):
        ok, reason = pre_flight_check("This fucking saree is amazing")
        assert ok is False
        assert "inappropriate language" in reason.lower()

    def test_email_in_input_blocked(self):
        ok, reason = pre_flight_check("Contact me at seller@example.com for bulk orders")
        assert ok is False
        assert "email" in reason.lower()

    def test_phone_number_in_input_blocked(self):
        ok, reason = pre_flight_check("Call us at 9876543210 for wholesale")
        assert ok is False
        assert "phone" in reason.lower()

    def test_normal_price_not_mistaken_for_phone(self):
        ok, _ = pre_flight_check("Price range ₹800 to ₹1200")
        assert ok is True

    def test_case_insensitive_profanity(self):
        ok, _ = pre_flight_check("SHIT quality")
        assert ok is False


class TestPostFlightClean:
    def test_empty_string_unchanged(self):
        assert post_flight_clean("") == ""

    def test_url_removed(self):
        result = post_flight_clean("Buy at https://amazon.in/product/123")
        assert "https://" not in result
        assert "[link removed]" in result

    def test_email_removed(self):
        result = post_flight_clean("Contact seller@example.com for details")
        assert "@" not in result
        assert "[email removed]" in result

    def test_phone_removed(self):
        result = post_flight_clean("WhatsApp 9876543210 for bulk")
        assert "9876543210" not in result
        assert "[number removed]" in result

    def test_clean_text_unchanged(self):
        text = "1. Use kanjivaram silk for premium appeal.\n2. Price at ₹900 for the value band."
        result = post_flight_clean(text)
        assert result == text

    def test_excessive_lines_truncated(self):
        long_text = "\n".join(f"Line {i}" for i in range(50))
        result = post_flight_clean(long_text)
        lines = result.splitlines()
        assert len(lines) <= 31  # 30 content + 1 truncation notice
        assert "truncated" in result.lower()

    def test_short_text_not_truncated(self):
        text = "Line 1\nLine 2\nLine 3"
        assert post_flight_clean(text) == text
