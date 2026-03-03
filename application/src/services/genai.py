"""Agentic GenAI service for Rivet — Draft → Critic loop.

Routing policy
--------------
DRAFT_MODEL_ID   (env)  — fast/cheap model for initial tips generation
                          default: anthropic.claude-3-5-haiku-20241022-v1:0
CRITIC_MODEL_ID  (env)  — high-stakes model for quality evaluation
                          default: anthropic.claude-3-5-sonnet-20241022-v2:0
VISION_MODEL_ID  (env)  — optional model for image attribute extraction
                          if unset, vision assist is skipped gracefully

USE_BEDROCK      (env)  — if true, use AWS Bedrock instead of Anthropic API
                          default: true

Critic rubric
-------------
Each dimension scored 0–25, total 0–100.
If total < CRITIC_THRESHOLD (75): apply edits / use improved version, retry once.

Telemetry fields returned
-------------------------
genai_tips         — final tips text
genai_model        — draft model used
genai_latency_ms   — total ms for draft(+retry)
genai_score        — critic total score
genai_rubric       — {clarity, actionability, on_brand, length} → 0–25 each
genai_vision       — {fabric, palette} if vision assist ran, else {}
"""
import json
import logging
import os
import time
from typing import Any, Generator

from .circuit_breaker import CircuitBreaker

# Use Bedrock client instead of Anthropic SDK
USE_BEDROCK = os.environ.get("USE_BEDROCK", "true").lower() in ("1", "true", "yes")

if USE_BEDROCK:
    from .bedrock_client import BedrockClient as AnthropicClient
else:
    import anthropic
    AnthropicClient = anthropic.Anthropic

log = logging.getLogger(__name__)

# Module-level circuit breaker singleton (one per process/worker)
_circuit_breaker = CircuitBreaker()

# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------
CRITIC_RUBRIC: dict[str, str] = {
    "clarity": "Tips are clear, jargon-free — max 2 industry terms per tip",
    "actionability": "Each tip specifies a concrete action and expected outcome",
    "on_brand": "Tips reference Indian ethnic wear market context or data",
    "length": "Total response is 250 words or fewer",
}
CRITIC_THRESHOLD = 75


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def _draft_model() -> str:
    return os.environ.get("DRAFT_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")


def _critic_model() -> str:
    return os.environ.get("CRITIC_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")


def _vision_model() -> str | None:
    return os.environ.get("VISION_MODEL_ID") or None


def _client(api_key: str = None) -> AnthropicClient:
    """Create Anthropic/Bedrock client.
    
    Args:
        api_key: API key (ignored if USE_BEDROCK=true)
    
    Returns:
        Client instance (Bedrock or Anthropic)
    """
    if USE_BEDROCK:
        return AnthropicClient()
    else:
        return AnthropicClient(api_key=api_key)


# ---------------------------------------------------------------------------
# Draft
# ---------------------------------------------------------------------------

def _draft_prompt(context: str, analysis_result: dict) -> str:
    return (
        "You are an experienced product development consultant specializing in Indian ethnic wear, "
        "helping designers refine their concepts for successful market launch.\n\n"
        f"DESIGN CONTEXT:\n{context}\n\n"
        "EVALUATION SUMMARY:\n"
        f"- Category: {analysis_result.get('category', 'ethnic wear')}\n"
        f"- Assessment: {analysis_result.get('classification', 'MODIFY')}\n"
        f"- Market Fit Score: {analysis_result.get('total_score', 50)}/100\n\n"
        "Provide 3-4 specific, actionable recommendations to enhance this design's market success.\n\n"
        "GUIDELINES:\n"
        "- Be constructive and encouraging - focus on opportunities\n"
        "- Each tip: specific action + expected customer/market benefit\n"
        "- Reference market trends and customer preferences (not 'data' or 'dataset')\n"
        "- Use business-friendly language\n"
        "- Keep total response under 250 words\n"
        "- Format as numbered list (1., 2., 3., 4.) with no preamble\n\n"
        "Focus on practical improvements that will increase customer appeal and market competitiveness."
    )


def draft(
    client: AnthropicClient,
    context: str,
    analysis_result: dict,
) -> tuple[str, str, int]:
    """Return (tips_text, model_used, latency_ms)."""
    model = _draft_model()
    t0 = time.monotonic()
    response = client.messages.create(
        model=model,
        max_tokens=450,
        messages=[{"role": "user", "content": _draft_prompt(context, analysis_result)}],
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    return response.content[0].text.strip(), model, latency_ms


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------

def _parse_critic_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON from critic response."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("Critic returned non-JSON: %.200s", text)
        return {"rubric_scores": {}, "total_score": 0, "edits": [], "improved_tips": ""}


def critique(client: AnthropicClient, tips_text: str) -> dict:
    """Evaluate tips against rubric.

    Returns:
        {
          "rubric_scores": {"clarity":int, "actionability":int,
                            "on_brand":int, "length":int},
          "total_score": int (0-100),
          "edits": [str, ...],
          "improved_tips": str   # non-empty only when total_score < 75
        }
    """
    rubric_lines = "\n".join(f"- {k}: {v}" for k, v in CRITIC_RUBRIC.items())
    prompt = (
        "You are a quality reviewer for product development recommendations.\n\n"
        f"QUALITY CRITERIA (each dimension 0-25):\n{rubric_lines}\n\n"
        f"RECOMMENDATIONS TO REVIEW:\n{tips_text}\n\n"
        "Evaluate each criterion (0-25 points). "
        "If total score < 75, provide specific improvements and an enhanced version.\n\n"
        "IMPORTANT: Ensure recommendations are:\n"
        "- Constructive and encouraging\n"
        "- Free of technical jargon (no 'dataset', 'data points', etc.)\n"
        "- Focused on business outcomes and customer benefits\n\n"
        "Respond ONLY with this exact JSON (no markdown):\n"
        '{"rubric_scores":{"clarity":0,"actionability":0,"on_brand":0,"length":0},'
        '"total_score":0,"edits":[],"improved_tips":""}'
    )
    response = client.messages.create(
        model=_critic_model(),
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_critic_json(response.content[0].text)


# ---------------------------------------------------------------------------
# Vision assist (optional)
# ---------------------------------------------------------------------------

def vision_assist(api_key: str, image_path: str, mime_type: str) -> dict[str, str]:
    """Extract fabric and palette from image using VISION_MODEL_ID.

    Returns {"fabric": str, "palette": str} or {} on any failure.
    """
    model = _vision_model()
    if not model:
        return {}
    try:
        import base64

        with open(image_path, "rb") as f:
            img_b64 = base64.standard_b64encode(f.read()).decode()

        client = _client(api_key)
        response = client.messages.create(
            model=model,
            max_tokens=120,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Examine this ethnic wear design concept. "
                                "Identify the fabric type and color palette. "
                                "Reply ONLY with JSON: "
                                '{"fabric":"<primary fabric type>","palette":"<2-3 main colors>"}'
                            ),
                        },
                    ],
                }
            ],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception as exc:
        log.warning("Vision assist failed (non-fatal): %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Main public function — Draft → Critic loop
# ---------------------------------------------------------------------------

def generate_grounded_tips(
    api_key: str,
    context: str,
    analysis_result: dict,
) -> dict[str, Any]:
    """Run the full Draft → Critic (→ optional retry) pipeline.

    Returns a dict with genai_* keys to merge into the analysis response.
    Never raises — returns empty genai fields on any failure.
    """
    if not os.environ.get("GENAI_ENABLED", "true").lower() in ("1", "true", "yes"):
        return _empty_genai()

    if _circuit_breaker.is_open():
        log.warning("GenAI circuit breaker OPEN — skipping tips")
        return _empty_genai()

    client = _client(api_key)
    total_latency = 0

    try:
        # ── Step 1: Draft ────────────────────────────────────────────────
        tips_text, model_used, latency_ms = draft(client, context, analysis_result)
        total_latency += latency_ms

        # ── Step 2: Critique ─────────────────────────────────────────────
        critique_result = critique(client, tips_text)
        score = critique_result.get("total_score", 0)

        # ── Step 3: Retry once if below threshold ────────────────────────
        if score < CRITIC_THRESHOLD:
            improved = critique_result.get("improved_tips", "").strip()
            if improved:
                tips_text = improved
                log.info("Critic improved tips (score was %d)", score)
            else:
                edits_ctx = (
                    context
                    + "\n\nPREVIOUS DRAFT FEEDBACK:\n"
                    + "\n".join(critique_result.get("edits", []))
                )
                tips_text, _, extra_ms = draft(client, edits_ctx, analysis_result)
                total_latency += extra_ms
                critique_result = critique(client, tips_text)
                score = critique_result.get("total_score", 0)
                log.info("Retry critic score: %d", score)

        _circuit_breaker.record_success()
        return {
            "genai_tips": tips_text,
            "genai_model": model_used,
            "genai_latency_ms": total_latency,
            "genai_score": score,
            "genai_rubric": critique_result.get("rubric_scores", {}),
        }

    except Exception as exc:
        log.error("GenAI pipeline failed: %s", exc)
        _circuit_breaker.record_failure()
        return _empty_genai()


# ---------------------------------------------------------------------------
# SSE streaming helper
# ---------------------------------------------------------------------------

def draft_stream(
    api_key: str,
    context: str,
    analysis_result: dict,
) -> Generator[str, None, None]:
    """Yield SSE-formatted events streaming draft tips tokens.

    Each event: ``data: {"token": "..."}\\n\\n``
    Final event:  ``data: {"done": true, "critic_score": N}\\n\\n``
    Error event:  ``data: {"error": "..."}\\n\\n``
    """
    client = _client(api_key)
    full_text_parts: list[str] = []

    try:
        with client.messages.stream(
            model=_draft_model(),
            max_tokens=450,
            messages=[
                {"role": "user", "content": _draft_prompt(context, analysis_result)}
            ],
        ) as stream:
            for token in stream.text_stream:
                full_text_parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

        # Run critic on the accumulated text
        full_text = "".join(full_text_parts)
        try:
            critique_result = critique(client, full_text)
            critic_score = critique_result.get("total_score", 0)
        except Exception:
            critic_score = 0

        yield f"data: {json.dumps({'done': True, 'critic_score': critic_score})}\n\n"

    except Exception as exc:
        log.error("SSE stream error: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_genai() -> dict[str, Any]:
    return {
        "genai_tips": "",
        "genai_model": "",
        "genai_latency_ms": 0,
        "genai_score": 0,
        "genai_rubric": {},
    }


def get_circuit_breaker() -> CircuitBreaker:
    """Expose the module-level circuit breaker (for tests / admin)."""
    return _circuit_breaker
