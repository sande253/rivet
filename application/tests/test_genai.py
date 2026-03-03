"""Tests for genai.py — prompt builder, rubric parsing, circuit breaker,
grounding helper, and vision assist fallback."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.services.circuit_breaker import CircuitBreaker
from src.services.genai import (
    _empty_genai,
    _parse_critic_json,
    CRITIC_THRESHOLD,
    generate_grounded_tips,
    get_circuit_breaker,
    vision_assist,
)


# ---------------------------------------------------------------------------
# Critic JSON parser
# ---------------------------------------------------------------------------

class TestParseCriticJson:
    def test_parses_valid_json(self):
        raw = json.dumps({
            "rubric_scores": {"clarity": 20, "actionability": 22, "on_brand": 18, "length": 23},
            "total_score": 83,
            "edits": [],
            "improved_tips": "",
        })
        result = _parse_critic_json(raw)
        assert result["total_score"] == 83
        assert result["rubric_scores"]["clarity"] == 20

    def test_strips_markdown_fences(self):
        raw = "```json\n{\"total_score\": 70, \"rubric_scores\": {}, \"edits\": [], \"improved_tips\": \"\"}\n```"
        result = _parse_critic_json(raw)
        assert result["total_score"] == 70

    def test_strips_backtick_fence_without_json_label(self):
        raw = "```\n{\"total_score\": 60, \"rubric_scores\": {}, \"edits\": [], \"improved_tips\": \"\"}\n```"
        result = _parse_critic_json(raw)
        assert result["total_score"] == 60

    def test_invalid_json_returns_empty(self):
        result = _parse_critic_json("not json at all")
        assert result["total_score"] == 0
        assert result["edits"] == []

    def test_missing_fields_handled(self):
        raw = json.dumps({"total_score": 55})
        result = _parse_critic_json(raw)
        assert result["total_score"] == 55
        assert result.get("improved_tips") is None  # not present → OK


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, window_seconds=60, circuit_timeout_seconds=10)
        assert not cb.is_open()
        assert cb.state == CircuitBreaker.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, window_seconds=60, circuit_timeout_seconds=10)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()
        assert cb.state == CircuitBreaker.OPEN

    def test_success_before_threshold_does_not_open(self):
        cb = CircuitBreaker(failure_threshold=3, window_seconds=60, circuit_timeout_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert not cb.is_open()

    def test_half_open_after_timeout(self):
        import time
        cb = CircuitBreaker(failure_threshold=2, window_seconds=60, circuit_timeout_seconds=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        time.sleep(1.1)
        assert not cb.is_open()
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_recovery_closes_circuit(self):
        import time
        cb = CircuitBreaker(failure_threshold=2, window_seconds=60, circuit_timeout_seconds=1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(1.1)
        cb.is_open()  # transitions to HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_reset_clears_state(self):
        cb = CircuitBreaker(failure_threshold=2, window_seconds=60, circuit_timeout_seconds=300)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        cb.reset()
        assert not cb.is_open()
        assert cb.state == CircuitBreaker.CLOSED


# ---------------------------------------------------------------------------
# generate_grounded_tips (mocking Anthropic client)
# ---------------------------------------------------------------------------

def _make_mock_response(text: str):
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


class TestGenerateGroundedTips:
    def test_returns_genai_fields_on_success(self):
        draft_text = "1. Use kanjivaram silk.\n2. Price at ₹900."
        critic_json = json.dumps({
            "rubric_scores": {"clarity": 22, "actionability": 20, "on_brand": 21, "length": 23},
            "total_score": 86,
            "edits": [],
            "improved_tips": "",
        })

        with patch("application.src.services.genai._client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = [
                _make_mock_response(draft_text),   # draft call
                _make_mock_response(critic_json),  # critic call
            ]
            mock_client_fn.return_value = mock_client

            result = generate_grounded_tips(
                api_key="test-key",
                context="GROUNDED CONTEXT: SAREE\nMarket avg price: ₹812",
                analysis_result={
                    "category": "Saree",
                    "classification": "LAUNCH",
                    "total_score": 78,
                },
            )

        assert result["genai_tips"] == draft_text
        assert result["genai_score"] == 86
        assert result["genai_model"] == "claude-haiku-4-5-20251001"
        assert result["genai_latency_ms"] >= 0

    def test_retry_on_low_critic_score(self):
        draft_text = "1. Initial tip."
        retry_text = "1. Better tip.\n2. Another tip."
        low_score_json = json.dumps({
            "rubric_scores": {"clarity": 10, "actionability": 10, "on_brand": 10, "length": 10},
            "total_score": 40,
            "edits": ["Be more specific"],
            "improved_tips": "",
        })
        high_score_json = json.dumps({
            "rubric_scores": {"clarity": 22, "actionability": 20, "on_brand": 21, "length": 22},
            "total_score": 85,
            "edits": [],
            "improved_tips": "",
        })

        with patch("application.src.services.genai._client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = [
                _make_mock_response(draft_text),     # first draft
                _make_mock_response(low_score_json), # first critique → low
                _make_mock_response(retry_text),     # retry draft
                _make_mock_response(high_score_json),# retry critique → high
            ]
            mock_client_fn.return_value = mock_client

            result = generate_grounded_tips(
                api_key="test-key",
                context="context",
                analysis_result={"category": "Saree", "classification": "MODIFY", "total_score": 55},
            )

        assert result["genai_tips"] == retry_text
        assert result["genai_score"] == 85

    def test_uses_improved_tips_when_provided(self):
        draft_text = "1. Initial weak tip."
        improved = "1. Use silk. Expected: 20% premium.\n2. Target ₹900 band."
        low_with_improved = json.dumps({
            "rubric_scores": {"clarity": 10, "actionability": 10, "on_brand": 10, "length": 10},
            "total_score": 40,
            "edits": [],
            "improved_tips": improved,
        })

        with patch("application.src.services.genai._client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = [
                _make_mock_response(draft_text),
                _make_mock_response(low_with_improved),
            ]
            mock_client_fn.return_value = mock_client

            result = generate_grounded_tips(
                api_key="test-key",
                context="ctx",
                analysis_result={"category": "Saree", "classification": "MODIFY", "total_score": 50},
            )

        assert result["genai_tips"] == improved
        # Should NOT have made a third API call
        assert mock_client.messages.create.call_count == 2

    def test_circuit_breaker_open_returns_empty(self):
        cb = CircuitBreaker(failure_threshold=1, window_seconds=60, circuit_timeout_seconds=300)
        cb.record_failure()  # opens circuit

        # Patch module-level circuit breaker
        with patch("application.src.services.genai._circuit_breaker", cb):
            result = generate_grounded_tips(
                api_key="test-key",
                context="ctx",
                analysis_result={},
            )

        assert result == _empty_genai()

    def test_exception_returns_empty_and_records_failure(self):
        with patch("application.src.services.genai._client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API error")
            mock_client_fn.return_value = mock_client

            cb = CircuitBreaker(failure_threshold=5, window_seconds=60, circuit_timeout_seconds=300)
            with patch("application.src.services.genai._circuit_breaker", cb):
                result = generate_grounded_tips(
                    api_key="test-key",
                    context="ctx",
                    analysis_result={},
                )
            assert result == _empty_genai()
            assert len(cb._failure_times) == 1


# ---------------------------------------------------------------------------
# Vision assist fallback
# ---------------------------------------------------------------------------

class TestVisionAssist:
    def test_returns_empty_dict_when_no_vision_model(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        with patch.dict("os.environ", {"VISION_MODEL_ID": ""}):
            result = vision_assist("test-key", str(img), "image/png")
        assert result == {}

    def test_returns_fabric_and_palette_on_success(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        vision_json = json.dumps({"fabric": "kanjivaram silk", "palette": "gold, red, green"})

        with patch.dict("os.environ", {"VISION_MODEL_ID": "claude-sonnet-4-6"}):
            with patch("application.src.services.genai._client") as mock_client_fn:
                mock_client = MagicMock()
                mock_client.messages.create.return_value = _make_mock_response(vision_json)
                mock_client_fn.return_value = mock_client

                result = vision_assist("test-key", str(img), "image/png")

        assert result["fabric"] == "kanjivaram silk"
        assert result["palette"] == "gold, red, green"

    def test_returns_empty_on_api_failure(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

        with patch.dict("os.environ", {"VISION_MODEL_ID": "claude-sonnet-4-6"}):
            with patch("application.src.services.genai._client") as mock_client_fn:
                mock_client = MagicMock()
                mock_client.messages.create.side_effect = Exception("Vision API down")
                mock_client_fn.return_value = mock_client

                result = vision_assist("test-key", str(img), "image/png")

        assert result == {}
