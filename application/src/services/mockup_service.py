"""Mockup generation service.

Local mode  (ENVIRONMENT != 'production'):
    PIL-based contrast/saturation/sharpen simulation.
    Returns /static/… URLs served by Flask.

Production mode (ENVIRONMENT=production):
    Amazon Bedrock Titan Image Generator v2 — IMAGE_VARIATION task.
    similarityStrength is configurable (default 0.65) — preserves garment
    silhouette and pose from sketch while adding photorealism.
    IAM-role credentials — no hardcoded keys.
    Uploads sketch + generated mockup to S3 via presigned URLs.
    Returns https://… presigned S3 URLs.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Final

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BEDROCK_DEFAULT_MODEL: Final = "amazon.titan-image-generator-v2:0"
_IMAGE_SIZE: Final = 512          # Titan v2 constraint: 256–2048, multiples of 64
_PRESIGNED_URL_TTL: Final = 3600  # seconds

# Per-category base prompts — tightly scoped to avoid garment confusion
_CATEGORY_CONTEXT: Final[dict[str, str]] = {
    "saree": (
        "Indian woman wearing a traditional silk saree: 6-yard draped fabric, "
        "pleated front pallu draped over left shoulder, matching silk blouse, "
        "visible petticoat hem, intricate zari border"
    ),
    "lehenga": (
        "Indian woman wearing a bridal lehenga choli: heavily embroidered "
        "full-length flared skirt, cropped choli blouse, sheer dupatta scarf "
        "draped over head or shoulders"
    ),
    "salwar_suit": (
        "Indian woman wearing salwar kameez: fitted churidar pants, "
        "knee-length straight-cut kameez tunic, matching dupatta"
    ),
    "kurti": (
        "Indian woman wearing ONLY a kurti tunic top with pants: "
        "straight knee-length tunic top, NO saree, NO draping, NO pallu over shoulder, "
        "simple embroidered tunic worn with churidar pants or leggings, "
    ),
    "kurta": (
        "Indian man wearing a traditional kurta with dhoti pants: "
        "long straight-cut kurta tunic with embroidery at collar and cuffs, "
        "loose pleated dhoti-style pants, formal shoes, male model, full body"
    ),
    "kurta_pyjama": (
        "Indian man wearing kurta pyjama: long straight-cut kurta, "
        "matching straight-leg pyjama pants, male model, full body"
    ),
    "sherwani": (
        "Indian man wearing a sherwani: long embroidered coat-style jacket "
        "with mandarin collar, churidar pants, groom or formal wear, male model, full body"
    ),
}

_NEGATIVE_PROMPT_BASE: Final = (
    "sketch, line drawing, cartoon, illustration, watercolor, anime, "
    "low quality, blurry, out of focus, grainy, noisy, artifacts, "
    "watermark, text, logo, signature, deformed body, extra limbs, "
    "missing limbs, disfigured, ugly face, bad anatomy, "
    "mannequin, doll, plastic skin, "
    "dark background, patterned background, gradient background, "
    "garment confusion, wrong clothing type"
)

_NEGATIVE_PROMPT_MENSWEAR: Final = (
    _NEGATIVE_PROMPT_BASE + ", "
    "woman, female, saree, lehenga, dupatta, pallu, blouse, skirt, "
    "women's clothing, feminine garment"
)

_NEGATIVE_PROMPT_WOMENSWEAR: Final = (
    _NEGATIVE_PROMPT_BASE + ", "
    "man, male, kurta, dhoti, sherwani, men's clothing"
)

# Anti-saree negative prompt for kurti (most confused category)
_NEGATIVE_PROMPT_KURTI: Final = (
    "sketch, cartoon, blurry, watermark, deformed, mannequin, "
    "dark background, "
    "saree, sari, draped fabric, pallu, pleated saree, 6-yard drape, "
    "petticoat, saree blouse, saree border, wrapped fabric, "
    "man, male, dhoti, sherwani"
)

# Menswear categories — used to select the right negative prompt
_MENSWEAR_CATEGORIES: Final = frozenset({"kurta", "kurta_pyjama", "sherwani"})

# ---------------------------------------------------------------------------
# Config dataclass — centralises all tunable parameters
# ---------------------------------------------------------------------------

@dataclass
class MockupConfig:
    """Runtime configuration for mockup generation."""

    environment: str = field(
        default_factory=lambda: os.environ.get("ENVIRONMENT", "local").lower()
    )
    bedrock_model_id: str = field(
        default_factory=lambda: os.environ.get("BEDROCK_IMAGE_MODEL_ID", _BEDROCK_DEFAULT_MODEL)
    )
    aws_region: str = field(
        default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1")
    )
    s3_bucket: str = field(
        default_factory=lambda: os.environ.get("S3_BUCKET", "")
    )
    # 0.2 = max photorealism (loose sketch structure)
    # 0.5 = balanced; 0.65 = preserves garment silhouette (recommended)
    # 0.8 = very close to sketch (less photorealistic)
    similarity_strength: float = field(
        default_factory=lambda: float(os.environ.get("SIMILARITY_STRENGTH", "0.65"))
    )
    cfg_scale: float = field(
        default_factory=lambda: float(os.environ.get("CFG_SCALE", "10.0"))
    )
    seed: int = field(
        default_factory=lambda: int(os.environ.get("GENERATION_SEED", "0"))
        # seed=0 means random; deterministic results: set a fixed integer
    )

    @property
    def is_production(self) -> bool:
        return self.environment in ("production", "prod")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _get_negative_prompt(category: str) -> str:
    """Return the appropriate negative prompt based on garment gender category."""
    if category in _MENSWEAR_CATEGORIES:
        return _NEGATIVE_PROMPT_MENSWEAR
    if category == "kurti":
        return _NEGATIVE_PROMPT_KURTI  # Special anti-saree prompt
    if category in ("saree", "lehenga", "salwar_suit"):
        return _NEGATIVE_PROMPT_WOMENSWEAR
    return _NEGATIVE_PROMPT_BASE


def _build_prompt(category: str, description: str) -> str:
    """
    Compose a Bedrock-safe (<512 chars) generation prompt.

    The category base anchors the garment type; the trimmed description
    adds product-specific detail (colour, print, embroidery, occasion, etc.).
    """
    base = _CATEGORY_CONTEXT.get(category, "Person wearing Indian ethnic wear")
    # Reserve ~100 chars for suffix; description trimmed to fit
    description = description.strip()
    max_desc = 512 - len(base) - 80
    if description:
        extra = f". {description[:max(0, max_desc)]}"
    else:
        extra = ""

    prompt = (
        f"{base}{extra}. "
        "Fashion editorial photography, full body shot, "
        "even studio lighting, pure white seamless background, "
        "hyper-realistic fabric texture, 8K detail"
    )
    # Hard cap — Titan v2 rejects prompts > 512 chars
    return prompt[:512]


# ---------------------------------------------------------------------------
# Local mode — PIL simulation
# ---------------------------------------------------------------------------

def _pil_enhance(src_path: str, dest_path: str) -> None:
    """Apply contrast/colour/sharpness pipeline to simulate a rendered mockup."""
    from PIL import Image, ImageEnhance, ImageFilter  # type: ignore[import]

    with Image.open(src_path) as img:
        img = img.convert("RGB").resize((_IMAGE_SIZE, _IMAGE_SIZE), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Color(img).enhance(1.3)
        img = ImageEnhance.Brightness(img).enhance(1.05)
        img = ImageEnhance.Sharpness(img).enhance(1.6)
        img = img.filter(ImageFilter.SMOOTH_MORE)
        img.save(dest_path, "PNG", optimize=True)


def _save_local(
    sketch_path: str, upload_folder: str, uid: str
) -> tuple[str, str]:
    from PIL import Image  # type: ignore[import]

    sketches_dir = os.path.join(upload_folder, "sketches")
    mockups_dir = os.path.join(upload_folder, "mockups")
    os.makedirs(sketches_dir, exist_ok=True)
    os.makedirs(mockups_dir, exist_ok=True)

    sketch_dest = os.path.join(sketches_dir, f"{uid}.png")
    mockup_dest = os.path.join(mockups_dir, f"{uid}_mockup.png")

    try:
        with Image.open(sketch_path) as img:
            img.convert("RGB").resize((_IMAGE_SIZE, _IMAGE_SIZE), Image.LANCZOS).save(
                sketch_dest, "PNG"
            )
    except Exception as exc:
        raise RuntimeError(f"Failed to process sketch image: {exc}") from exc

    try:
        _pil_enhance(sketch_path, mockup_dest)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate local mockup: {exc}") from exc

    log.warning(
        "LOCAL MODE: PIL-enhanced sketch only — not AI-generated. "
        "Set ENVIRONMENT=production to enable Bedrock."
    )

    rel = upload_folder.replace("\\", "/")
    url_base = ("/" + rel) if rel.startswith("static/") else ("/static/" + rel)
    return f"{url_base}/sketches/{uid}.png", f"{url_base}/mockups/{uid}_mockup.png"


# ---------------------------------------------------------------------------
# Production mode — Amazon Bedrock + S3
# ---------------------------------------------------------------------------

def _bedrock_client(region: str):
    import boto3  # type: ignore[import]
    import botocore.config  # type: ignore[import]

    cfg = botocore.config.Config(
        read_timeout=120,
        connect_timeout=15,
        retries={"max_attempts": 2, "mode": "standard"},
    )
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


def _prepare_sketch_b64(sketch_path: str) -> str:
    """
    Resize sketch to _IMAGE_SIZE × _IMAGE_SIZE and return as a base64 PNG string.

    Titan v2 IMAGE_VARIATION requires the reference image to be the same
    dimensions as the requested output.
    """
    from PIL import Image  # type: ignore[import]

    with Image.open(sketch_path) as img:
        img = img.convert("RGB").resize((_IMAGE_SIZE, _IMAGE_SIZE), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    log.debug("Sketch prepared for Bedrock: %dx%d, b64_len=%d", _IMAGE_SIZE, _IMAGE_SIZE, len(b64))
    return b64


def _bedrock_generate(prompt: str, sketch_path: str, cfg: MockupConfig, category: str) -> bytes:
    """
    Call Bedrock Titan IMAGE_VARIATION and return raw PNG bytes.

    similarityStrength (cfg.similarity_strength):
        0.2  → maximum photorealism, loosely follows sketch pose/layout
        0.65 → preserves garment silhouette and pose (recommended default)
        0.8+ → stays very close to sketch structure, less photorealistic
    """
    sketch_b64 = _prepare_sketch_b64(sketch_path)
    negative_prompt = _get_negative_prompt(category)

    body = {
        "taskType": "IMAGE_VARIATION",
        "imageVariationParams": {
            "text": prompt,
            "negativeText": negative_prompt,
            "images": [sketch_b64],
            "similarityStrength": cfg.similarity_strength,
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": _IMAGE_SIZE,
            "height": _IMAGE_SIZE,
            "cfgScale": cfg.cfg_scale,
            "seed": cfg.seed,
        },
    }

    log.info(
        "Invoking Bedrock IMAGE_VARIATION [model=%s size=%dx%d similarity=%.2f seed=%d]",
        cfg.bedrock_model_id,
        _IMAGE_SIZE,
        _IMAGE_SIZE,
        cfg.similarity_strength,
        cfg.seed,
    )

    client = _bedrock_client(cfg.aws_region)

    try:
        response = client.invoke_model(
            modelId=cfg.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
    except Exception as exc:
        log.error("Bedrock invoke_model failed: %s", exc)
        raise RuntimeError(f"Bedrock API call failed: {exc}") from exc

    result = json.loads(response["body"].read())

    error = result.get("error")
    if error:
        log.error("Bedrock error response: %s", result)
        raise RuntimeError(f"Bedrock returned an error: {error}")

    images = result.get("images")
    if not images:
        log.error("Bedrock response missing 'images'. Response keys: %s", list(result.keys()))
        raise RuntimeError(
            f"Bedrock returned no images. Response keys: {list(result.keys())}"
        )

    log.info("Bedrock IMAGE_VARIATION succeeded.")
    return base64.standard_b64decode(images[0])


def _s3_upload(data: bytes, bucket: str, key: str, region: str) -> str:
    """Upload bytes to S3 and return a presigned GET URL."""
    import boto3  # type: ignore[import]

    s3 = boto3.client("s3", region_name=region)
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="image/png")
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=_PRESIGNED_URL_TTL,
    )
    log.info("S3 upload complete [key=%s ttl=%ds]", key, _PRESIGNED_URL_TTL)
    return url


def _save_production(
    sketch_path: str, mockup_bytes: bytes, uid: str, cfg: MockupConfig
) -> tuple[str, str]:
    if not cfg.s3_bucket:
        raise RuntimeError(
            "S3_BUCKET environment variable is required in production mode."
        )

    with open(sketch_path, "rb") as fh:
        sketch_bytes = fh.read()

    sketch_url = _s3_upload(
        sketch_bytes, cfg.s3_bucket, f"uploads/sketches/{uid}.png", cfg.aws_region
    )
    mockup_url = _s3_upload(
        mockup_bytes, cfg.s3_bucket, f"uploads/mockups/{uid}.png", cfg.aws_region
    )
    return sketch_url, mockup_url


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_mockup(
    sketch_path: str,
    category: str,
    description: str,
    upload_folder: str,
    *,
    config: MockupConfig | None = None,
) -> dict:
    """Generate a realistic mockup from a fashion sketch image.

    Args:
        sketch_path:   Absolute or CWD-relative path to the uploaded sketch file.
        category:      One of: saree | lehenga | salwar_suit | kurti.
        description:   Free-text product description (colour, fabric, embroidery…).
        upload_folder: Flask UPLOAD_FOLDER value (used only in local mode).
        config:        Optional MockupConfig override; defaults read from env vars.

    Returns:
        {
            "sketch_url":  str,   # URL of the stored sketch
            "mockup_url":  str,   # URL of the generated mockup
            "status":      "success",
            "mode":        "production" | "local",
            "uid":         str,
        }

    Raises:
        RuntimeError on any failure (caller should surface as HTTP 500).
    """
    if config is None:
        config = MockupConfig()

    uid = uuid.uuid4().hex
    prompt = _build_prompt(category, description)
    mode = "production" if config.is_production else "local"

    log.info(
        "Generating mockup [mode=%s uid=%s category=%s]",
        mode,
        uid,
        category,
    )
    log.debug("Prompt (%d chars): %s", len(prompt), prompt)

    try:
        if config.is_production:
            mockup_bytes = _bedrock_generate(prompt, sketch_path, config, category)
            sketch_url, mockup_url = _save_production(sketch_path, mockup_bytes, uid, config)
        else:
            sketch_url, mockup_url = _save_local(sketch_path, upload_folder, uid)

        log.info("Mockup complete [sketch=%s mockup=%s]", sketch_url, mockup_url)
        return {
            "sketch_url": sketch_url,
            "mockup_url": mockup_url,
            "status": "success",
            "mode": mode,
            "uid": uid,
        }

    except Exception as exc:
        log.error("Mockup generation failed [uid=%s]: %s", uid, exc, exc_info=True)
        raise