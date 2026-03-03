"""Pre- and post-flight safety checks for GenAI inputs/outputs.

Pre-flight  — run on user-submitted text before calling the AI.
             Returns (ok, reason); ok=False → skip GenAI, fall back to
             deterministic-only result.

Post-flight — run on AI-generated text before returning to the client.
             Strips URLs, emails, phone numbers; truncates excessive lines.
"""
import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profanity list — extend as needed
# ---------------------------------------------------------------------------
_PROFANITY: frozenset[str] = frozenset(
    [
        "damn", "hell", "crap", "ass", "bastard", "bitch",
        "fuck", "shit", "piss", "dick", "cock", "pussy",
        "nigger", "faggot", "retard",
    ]
)

# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
_RE_PHONE = re.compile(
    r"(?<!\d)(?:\+91[-\s]?)?\d{10}(?!\d)"  # Indian mobile numbers
)
_RE_CARD = re.compile(r"(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)")
_RE_URL = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.IGNORECASE)

_PII_PATTERNS = [_RE_EMAIL, _RE_PHONE, _RE_CARD]

MAX_OUTPUT_LINES = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pre_flight_check(text: str) -> tuple[bool, str]:
    """Return (ok, reason).  ok=False means skip GenAI entirely."""
    if not text:
        return True, ""

    lower = text.lower()

    # Profanity
    for word in _PROFANITY:
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            log.warning("Pre-flight blocked: profanity (%s)", word)
            return False, "Content policy violation: inappropriate language detected."

    # PII in input
    if _RE_EMAIL.search(text):
        log.warning("Pre-flight blocked: email address in input")
        return False, "Content policy violation: email address detected in input."
    if _RE_PHONE.search(text):
        log.warning("Pre-flight blocked: phone number in input")
        return False, "Content policy violation: phone number detected in input."

    return True, ""


def post_flight_clean(text: str) -> str:
    """Sanitise AI output before serving to the client."""
    if not text:
        return text

    # Strip URLs
    text = _RE_URL.sub("[link removed]", text)
    # Strip emails
    text = _RE_EMAIL.sub("[email removed]", text)
    # Strip phone numbers
    text = _RE_PHONE.sub("[number removed]", text)

    # Truncate excessive lines
    lines = text.splitlines()
    if len(lines) > MAX_OUTPUT_LINES:
        text = "\n".join(lines[:MAX_OUTPUT_LINES]) + "\n[…truncated]"

    return text
