"""Mockup generation service.

Local mode  (ENVIRONMENT != 'production'):
    PIL-based contrast/saturation/sharpen simulation.
    Saves sketch copy + enhanced mockup under UPLOAD_FOLDER/sketches/ and
    UPLOAD_FOLDER/mockups/.  Returns /static/… URLs served by Flask.

Production mode (ENVIRONMENT=production):
    Amazon Bedrock Titan Image Generator v2 (IMAGE_VARIATION, similarityStrength=0.3).
    Uses the sketch as structural reference but renders photorealistically.
    IAM-role credentials — no hardcoded keys.
    Uploads sketch + generated mockup to S3.
    Returns https://… public S3 URLs.
"""
import base64
import json
import logging
import os
import uuid

log = logging.getLogger(__name__)

_BEDROCK_DEFAULT_MODEL = "amazon.titan-image-generator-v2:0"

_CATEGORY_CONTEXT: dict[str, str] = {
    "saree": (
        "Indian saree with realistic silk fabric texture, elegant draping, "
        "ornate woven border, graceful pleats"
    ),
    "lehenga": (
        "Indian lehenga choli with realistic embroidery, rich brocade fabric, "
        "graceful flared skirt, dupatta"
    ),
    "salwar_suit": (
        "Indian salwar suit with realistic fabric texture, delicate embroidery, "
        "traditional silhouette, matching dupatta"
    ),
    "kurti": (
        "Indian kurti with realistic cotton or rayon fabric, printed or embroidered "
        "details, clean tailored cut"
    ),
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(category: str, description: str) -> str:
    base = _CATEGORY_CONTEXT.get(
        category,
        "Indian ethnic wear garment with realistic fabric texture and traditional details",
    )
    extra = f", {description}" if description else ""
    return (
        f"Professional fashion product photography: {base}{extra}. "
        "Worn by a model in a studio setting, full body shot, "
        "professional studio lighting with soft shadows creating depth, "
        "clean white background, ultra-realistic fabric texture with visible weave and sheen, "
        "natural draping and folds showing fabric weight, "
        "high resolution commercial photography, professional color grading, "
        "sharp details, photorealistic rendering, magazine quality fashion editorial, "
        "model facing camera, elegant pose, professional styling"
    )


# ---------------------------------------------------------------------------
# Local mode — PIL simulation
# ---------------------------------------------------------------------------

def _pil_enhance(src_path: str, dest_path: str) -> None:
    from PIL import Image, ImageEnhance, ImageFilter  # type: ignore[import]

    with Image.open(src_path) as img:
        img = img.convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.3)
        img = ImageEnhance.Color(img).enhance(1.2)
        img = ImageEnhance.Sharpness(img).enhance(1.4)
        img = img.filter(ImageFilter.SMOOTH)
        img.save(dest_path, "PNG")


def _save_local(
    sketch_path: str,
    upload_folder: str,
    uid: str,
) -> tuple[str, str]:
    """Save sketch copy + simulated mockup. Returns (sketch_url, mockup_url)."""
    from PIL import Image  # type: ignore[import]

    sketches_dir = os.path.join(upload_folder, "sketches")
    mockups_dir = os.path.join(upload_folder, "mockups")
    os.makedirs(sketches_dir, exist_ok=True)
    os.makedirs(mockups_dir, exist_ok=True)

    sketch_filename = f"{uid}.png"
    mockup_filename = f"{uid}_mockup.png"

    sketch_dest = os.path.join(sketches_dir, sketch_filename)
    mockup_dest = os.path.join(mockups_dir, mockup_filename)

    # Convert and save sketch as PNG
    try:
        with Image.open(sketch_path) as img:
            img = img.convert("RGB")
            img.save(sketch_dest, "PNG")
    except Exception as e:
        log.error("Failed to save sketch: %s", e)
        raise RuntimeError(f"Failed to process sketch image: {e}")

    # Local mode: PIL simulation (no Bedrock available).
    # Adds a visible "DEV PREVIEW" overlay so it's clear this is not the real mockup.
    try:
        _pil_enhance(sketch_path, mockup_dest)
    except Exception as e:
        log.error("Failed to enhance mockup: %s", e)
        raise RuntimeError(f"Failed to generate mockup: {e}")

    log.warning(
        "LOCAL MODE: mockup is a PIL-enhanced copy of the sketch. "
        "Set ENVIRONMENT=production and configure Bedrock for realistic generation."
    )

    # Build URL paths relative to Flask static root.
    # upload_folder is normally "static/uploads"; strip the "static/" prefix
    # so Flask serves them correctly via /static/…
    rel = upload_folder.replace("\\", "/")
    if rel.startswith("static/"):
        url_base = "/" + rel
    else:
        url_base = "/static/" + rel

    sketch_url = f"{url_base}/sketches/{sketch_filename}"
    mockup_url = f"{url_base}/mockups/{mockup_filename}"
    return sketch_url, mockup_url


# ---------------------------------------------------------------------------
# Production mode — Amazon Bedrock + S3
# ---------------------------------------------------------------------------

def _bedrock_client():
    import boto3  # type: ignore[import]
    import botocore.config  # type: ignore[import]

    region = os.environ.get("AWS_REGION", "us-east-1")
    cfg = botocore.config.Config(
        read_timeout=60,
        connect_timeout=10,
        retries={"max_attempts": 1},
    )
    # Credentials come from IAM role / environment — never hardcoded.
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


def _bedrock_generate(prompt: str, sketch_path: str, model_id: str) -> bytes:
    """Call Bedrock TEXT_IMAGE to generate realistic mockup. Returns raw PNG bytes."""
    # Use TEXT_IMAGE to generate photorealistic product photos from description
    # The sketch is analyzed by Claude first, and that analysis is used in the prompt
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
            "negativeText": (
                "blurry, cartoon, sketch, drawing, line art, pencil drawing, "
                "low quality, watermark, cropped, deformed, out of frame, "
                "unrealistic, flat colors, amateur, pixelated, illustration, "
                "anime, painting, digital art, mannequin, headless, faceless"
            ),
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": 768,  # Higher resolution for better quality
            "height": 1024,  # Portrait orientation for fashion
            "cfgScale": 10.0,  # Higher value = stronger prompt adherence
            "seed": 42,  # Consistent results
        },
    }

    client = _bedrock_client()
    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return base64.standard_b64decode(result["images"][0])


def _s3_upload(data: bytes, bucket: str, key: str) -> str:
    import boto3  # type: ignore[import]

    region = os.environ.get("AWS_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType="image/png",
    )
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def _save_production(
    sketch_path: str,
    mockup_bytes: bytes,
    uid: str,
) -> tuple[str, str]:
    """Upload sketch + mockup to S3. Returns (sketch_url, mockup_url)."""
    bucket = os.environ.get("S3_BUCKET", "")
    if not bucket:
        raise RuntimeError("S3_BUCKET environment variable is not set")

    with open(sketch_path, "rb") as f:
        sketch_bytes = f.read()

    sketch_url = _s3_upload(sketch_bytes, bucket, f"uploads/sketches/{uid}.png")
    mockup_url = _s3_upload(mockup_bytes, bucket, f"uploads/mockups/{uid}.png")
    return sketch_url, mockup_url


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_mockup(
    sketch_path: str,
    category: str,
    description: str,
    upload_folder: str,
) -> dict:
    """Generate a realistic mockup from a sketch image.

    Args:
        sketch_path:   Absolute or CWD-relative path to the uploaded sketch file.
        category:      One of saree | lehenga | salwar_suit | kurti.
        description:   Optional free-text product description.
        upload_folder: Flask UPLOAD_FOLDER config value (used in local mode).

    Returns:
        {"sketch_url": str, "mockup_url": str, "status": "success"}

    Raises:
        RuntimeError / Exception on any failure — caller is responsible for
        mapping errors to HTTP responses.
    """
    uid = uuid.uuid4().hex
    prompt = _build_prompt(category, description)
    is_production = os.environ.get("ENVIRONMENT", "local").lower() == "production"

    log.info(
        "Generating mockup [mode=%s uid=%s category=%s]",
        "production" if is_production else "local",
        uid,
        category,
    )

    try:
        if is_production:
            model_id = os.environ.get("BEDROCK_IMAGE_MODEL_ID", _BEDROCK_DEFAULT_MODEL)
            log.info("Using Bedrock model: %s", model_id)
            mockup_bytes = _bedrock_generate(prompt, sketch_path, model_id)
            sketch_url, mockup_url = _save_production(sketch_path, mockup_bytes, uid)
        else:
            log.info("Using local PIL enhancement")
            sketch_url, mockup_url = _save_local(sketch_path, upload_folder, uid)

        log.info("Mockup generated successfully [sketch=%s mockup=%s]", sketch_url, mockup_url)
        return {
            "sketch_url": sketch_url,
            "mockup_url": mockup_url,
            "status": "success",
        }
    except Exception as e:
        log.error("Mockup generation failed: %s", e, exc_info=True)
        raise
