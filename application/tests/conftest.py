"""Shared test fixtures.

Run from the application/ directory:
    cd application
    pytest
"""
import os

import pytest

# Set env vars before any app import
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("GENAI_ENABLED", "true")
os.environ.setdefault("DRAFT_MODEL_ID", "claude-haiku-4-5-20251001")
os.environ.setdefault("CRITIC_MODEL_ID", "claude-sonnet-4-6")
os.environ.setdefault("GENAI_FAILURE_THRESHOLD", "3")
os.environ.setdefault("GENAI_CIRCUIT_TIMEOUT", "10")
os.environ.setdefault("GENAI_CACHE_TTL", "60")


@pytest.fixture()
def app():
    from src.app import create_app

    application = create_app("development")
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
