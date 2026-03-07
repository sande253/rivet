import os
import secrets


def _resolve_sqlite_path(db_url: str) -> str:
    """Convert relative SQLite paths to absolute paths for cross-platform compatibility.
    
    Examples:
        sqlite:///instance/rivet.db → sqlite:///C:/path/to/app/instance/rivet.db
        postgresql://... → postgresql://... (unchanged)
    """
    if not db_url.startswith("sqlite:///"):
        return db_url
    
    # Extract relative path from sqlite:///path
    rel_path = db_url.replace("sqlite:///", "", 1)
    
    # Resolve to absolute path from the application root (where this config.py is)
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    abs_path = os.path.join(app_root, rel_path)
    
    # Convert to forward slashes for SQLite URI (Windows compatibility)
    abs_path = abs_path.replace("\\", "/")
    
    # Return as sqlite:/// URI (on Windows: sqlite:///C:/path/to/file.db)
    return f"sqlite:///{abs_path}"


class Config:
    """Base configuration — values come from environment variables.

    Locally, populate a .env file (see .env.example).
    In ECS, inject these as task environment variables or via Secrets Manager.
    """
    # Security — always set SECRET_KEY in production via environment variable.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # Database — SQLite by default; swap DATABASE_URL for PostgreSQL in cloud.
    # Relative paths are converted to absolute for Windows compatibility.
    _db_url: str = os.environ.get("DATABASE_URL", "sqlite:///instance/rivet.db")
    SQLALCHEMY_DATABASE_URI: str = _resolve_sqlite_path(_db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Anthropic API Key — optional when using Bedrock (USE_BEDROCK=true)
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    UPLOAD_FOLDER: str = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    MAX_CONTENT_LENGTH: int = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 16)) * 1024 * 1024

    # Resolved at import time; __file__ is application/src/config.py
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")

    CATEGORY_CSV_MAP: dict = {
        "saree":       "clean_saree_data.csv",
        "lehenga":     "Lehenga_choli.csv",
        "salwar_suit": "salwar_suits.csv",
        "kurti":       "W_kurti.csv",
        "kurta":       "kurta.csv",
        "kurta_pyjama": "kurta_pyjama.csv",
        "sherwani":    "sherwani.csv",
    }

    CATEGORY_LABELS: dict = {
        "saree":       "Saree",
        "lehenga":     "Lehenga Choli",
        "salwar_suit": "Salwar Suit",
        "kurti":       "Kurti",
        "kurta":       "Kurta",
        "kurta_pyjama": "Kurta Pyjama",
        "sherwani":    "Sherwani",
    }

    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "webp"}

    # ── GenAI model routing ───────────────────────────────────────────────
    # USE_BEDROCK     — if true, use AWS Bedrock instead of Anthropic API
    # DRAFT_MODEL_ID  — fast model for initial tip generation
    # CRITIC_MODEL_ID — high-stakes model for quality evaluation
    # VISION_MODEL_ID — optional; omit to skip vision assist
    USE_BEDROCK: bool = os.environ.get("USE_BEDROCK", "true").lower() in ("1", "true", "yes")
    DRAFT_MODEL_ID: str = os.environ.get("DRAFT_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
    CRITIC_MODEL_ID: str = os.environ.get("CRITIC_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    VISION_MODEL_ID: str = os.environ.get("VISION_MODEL_ID", "")

    # ── Deployment environment ────────────────────────────────────────────
    # Set ENVIRONMENT=production in ECS / cloud deployments.
    # Any other value (or unset) is treated as local mode.
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "local")

    # ── Mockup generation (Bedrock + S3) — production only ───────────────
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
    BEDROCK_IMAGE_MODEL_ID: str = os.environ.get(
        "BEDROCK_IMAGE_MODEL_ID", "amazon.titan-image-generator-v2:0"
    )
    S3_BUCKET: str = os.environ.get("S3_BUCKET", "")

    # ── GenAI feature flags ───────────────────────────────────────────────
    GENAI_ENABLED: bool = os.environ.get("GENAI_ENABLED", "true").lower() in (
        "1", "true", "yes"
    )

    # ── Cache ─────────────────────────────────────────────────────────────
    GENAI_CACHE_TTL: int = int(os.environ.get("GENAI_CACHE_TTL", "300"))

    # ── Circuit breaker ───────────────────────────────────────────────────
    GENAI_FAILURE_THRESHOLD: int = int(os.environ.get("GENAI_FAILURE_THRESHOLD", "5"))
    GENAI_CIRCUIT_TIMEOUT: int = int(os.environ.get("GENAI_CIRCUIT_TIMEOUT", "300"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
