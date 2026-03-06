"""Mockup generation service.

Local mode  (ENVIRONMENT != 'production'):
    PIL-based contrast/saturation/sharpen simulation.
    Returns /static/… URLs served by Flask.

Production mode (ENVIRONMENT=production):
    Amazon Bedrock Titan Image Generator v2 — IMAGE_VARIATION task.
    similarityStrength=0.2 → loosely follows sketch structure, maximum photorealism.
    IAM-role credentials — no hardcoded keys.
    Uploads sketch + generated mockup to S3.
    Returns https://… public S3 URLs.
"""
import base64
import io
import json
import logging
import os
import uuid

log = logging.getLogger(__name__)

_BEDROCK_DEFAULT_MODEL = "amazon.titan-image-generator-v2:0"

_CATEGORY_CONTEXT: dict[str, str] = {
    "saree": "Indian saree, silk fabric, elegant draping, ornate border, vibrant colors",
    "lehenga": "Indian lehenga choli, embroidery, brocade, flared skirt, dupatta",
    "salwar_suit": "Indian salwar suit, embroidered fabric, traditional silhouette",
    "kurti": "Indian kurti, cotton fabric, printed details, tailored cut",
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(category: str, description: str) -> str:
    base = _CATEGORY_CONTEXT.get(
        category,
        "Indian ethnic wear, realistic fabric",
    )
    extra = f", {description[:100]}" if description else ""
    # Keep under 512 chars for Bedrock Titan limit
    return (
        f"Professional fashion photo: {base}{extra}. "
        "Indian woman model, full body, studio lighting, white background, "
        "photorealistic fabric texture, vivid colors, DSLR quality"
    )


def _build_negative_prompt() -> str:
    # Keep under 512 chars for Bedrock Titan limit
    return (
        "sketch, drawing, cartoon, illustration, blurry, low quality, "
        "watermark, text, deformed, ugly, cropped, mannequin, "
        "dark background, colored background"
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


def _save_local(sketch_path: str, upload_folder: str, uid: str) -> tuple[str, str]:
    from PIL import Image  # type: ignore[import]

    sketches_dir = os.path.join(upload_folder, "sketches")
    mockups_dir = os.path.join(upload_folder, "mockups")
    os.makedirs(sketches_dir, exist_ok=True)
    os.makedirs(mockups_dir, exist_ok=True)

    sketch_filename = f"{uid}.png"
    mockup_filename = f"{uid}_mockup.png"
    sketch_dest = os.path.join(sketches_dir, sketch_filename)
    mockup_dest = os.path.join(mockups_dir, mockup_filename)

    try:
        with Image.open(sketch_path) as img:
            img.convert("RGB").save(sketch_dest, "PNG")
    except Exception as e:
        raise RuntimeError(f"Failed to process sketch image: {e}") from e

    try:
        _pil_enhance(sketch_path, mockup_dest)
    except Exception as e:
        raise RuntimeError(f"Failed to generate mockup: {e}") from e

    log.warning("LOCAL MODE: PIL-enhanced sketch only. Set ENVIRONMENT=production for Bedrock.")

    rel = upload_folder.replace("\\", "/")
    url_base = ("/" + rel) if rel.startswith("static/") else ("/static/" + rel)
    return f"{url_base}/sketches/{sketch_filename}", f"{url_base}/mockups/{mockup_filename}"


# ---------------------------------------------------------------------------
# Production mode — Amazon Bedrock + S3
# ---------------------------------------------------------------------------

def _bedrock_client():
    import boto3  # type: ignore[import]
    import botocore.config  # type: ignore[import]

    region = os.environ.get("AWS_REGION", "us-east-1")
    cfg = botocore.config.Config(
        read_timeout=120,
        connect_timeout=15,
        retries={"max_attempts": 2},
    )
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


def _prepare_sketch_b64(sketch_path: str) -> str:
    """
    Resize sketch to 512x512 (Titan v2 supports 256-2048, multiples of 64)
    and return as base64 PNG string.
    """
    from PIL import Image  # type: ignore[import]

    with Image.open(sketch_path) as img:
        img = img.convert("RGB").resize((512, 512), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    log.debug("Sketch prepared for Bedrock: 512×512, b64_len=%d", len(b64))
    return b64


def _bedrock_generate(prompt: str, sketch_path: str, model_id: str) -> bytes:
    """
    Call Bedrock Titan IMAGE_VARIATION.

    The sketch is passed as images[0] — Titan uses it as a structural/
    compositional guide.  similarityStrength=0.2 gives maximum photorealism
    while loosely preserving the garment pose and layout from the sketch.
    Increase to 0.4–0.5 to stay closer to the sketch structure.
    """
    sketch_b64 = _prepare_sketch_b64(sketch_path)

    body = {
        "taskType": "IMAGE_VARIATION",
        "imageVariationParams": {
            "text": prompt,
            "negativeText": _build_negative_prompt(),
            "images": [sketch_b64],
            "similarityStrength": 0.2,   # 0.2 = loose structure, max photorealism
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": 512,
            "height": 512,
            "cfgScale": 10.0,
            "seed": 42,
        },
    }

    log.info("Invoking Bedrock IMAGE_VARIATION [model=%s size=512x512 similarity=0.2]", model_id)
    client = _bedrock_client()

    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
    except Exception as e:
        log.error("Bedrock invoke_model failed: %s", e)
        raise RuntimeError(f"Bedrock API call failed: {e}") from e

    result = json.loads(response["body"].read())

    if "error" in result:
        raise RuntimeError(f"Bedrock returned error: {result['error']}")

    if not result.get("images"):
        raise RuntimeError(f"Bedrock returned no images. Keys: {list(result.keys())}")

    log.info("Bedrock IMAGE_VARIATION succeeded.")
    return base64.standard_b64decode(result["images"][0])


def _s3_upload(data: bytes, bucket: str, key: str, region: str) -> str:
    import boto3  # type: ignore[import]

    s3 = boto3.client("s3", region_name=region)
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="image/png")
    
    # Generate presigned URL (valid for 1 hour)
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600
    )
    log.info("Uploaded to S3 with presigned URL: %s", key)
    return url


def _save_production(sketch_path: str, mockup_bytes: bytes, uid: str) -> tuple[str, str]:
    bucket = os.environ.get("S3_BUCKET", "")
    if not bucket:
        raise RuntimeError("S3_BUCKET environment variable is not set")

    region = os.environ.get("AWS_REGION", "us-east-1")

    with open(sketch_path, "rb") as f:
        sketch_bytes = f.read()

    sketch_url = _s3_upload(sketch_bytes, bucket, f"uploads/sketches/{uid}.png", region)
    mockup_url = _s3_upload(mockup_bytes, bucket, f"uploads/mockups/{uid}.png", region)
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
        RuntimeError / Exception on any failure.
    """
    uid = uuid.uuid4().hex
    prompt = _build_prompt(category, description)
    env = os.environ.get("ENVIRONMENT", "local").lower()
    is_production = env in ("production", "prod")

    log.info(
        "Generating mockup [mode=%s uid=%s category=%s env=%s]",
        "production" if is_production else "local",
        uid,
        category,
        env,
    )
    log.debug("Prompt: %s", prompt)

    try:
        if is_production:
            model_id = os.environ.get("BEDROCK_IMAGE_MODEL_ID", _BEDROCK_DEFAULT_MODEL)
            mockup_bytes = _bedrock_generate(prompt, sketch_path, model_id)
            sketch_url, mockup_url = _save_production(sketch_path, mockup_bytes, uid)
        else:
            sketch_url, mockup_url = _save_local(sketch_path, upload_folder, uid)

        log.info("Mockup done [sketch=%s mockup=%s]", sketch_url, mockup_url)
        return {"sketch_url": sketch_url, "mockup_url": mockup_url, "status": "success"}

    except Exception as e:
        log.error("Mockup generation failed: %s", e, exc_info=True)
        raise