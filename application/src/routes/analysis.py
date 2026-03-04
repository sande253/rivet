"""Analysis routes.

POST /analyze          — full analysis (deterministic + GenAI tips)
GET  /analyze/stream   — SSE streaming of Draft tips
POST /generate-mockup  — sketch → realistic mockup image generation
"""
import csv
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_login import login_required
from werkzeug.utils import secure_filename

from ..services.claude_service import analyze_sketch_with_claude
from ..services.market_service import build_context, load_df

analysis_bp = Blueprint("analysis", __name__)
log = logging.getLogger(__name__)

_MIME_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

_RESULTS_FILE = "analysis_results.csv"
_RESULTS_FIELDS = [
    "id", "timestamp", "category", "filename", "description", "price",
    "total_score", "classification",
    "genai_tips", "genai_model", "genai_latency_ms", "genai_score",
]


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------

@analysis_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    if "sketch" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["sketch"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP"}), 400

    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    category_labels = current_app.config["CATEGORY_LABELS"]
    category = request.form.get("category", "saree").strip().lower()
    if category not in category_csv_map:
        return jsonify({
            "error": (
                f"Unknown category '{category}'. "
                f"Valid options: {', '.join(category_csv_map.keys())}"
            )
        }), 400

    filename = secure_filename(file.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[1].lower()
    mime_type = _MIME_MAP.get(ext, "image/jpeg")

    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()

    try:
        # ── Core deterministic analysis (Claude vision) ───────────────────
        result = analyze_sketch_with_claude(filepath, mime_type, category)
        result["image_url"] = f"/static/uploads/{filename}"
    
    except ValueError as exc:
        # Handle non-fashion image rejection
        log.info("Image rejected (not fashion): %s", exc)
        return jsonify({"error": str(exc)}), 400

        # ── Optional: vision assist for fabric/palette extraction ─────────
        # API key is optional when using Bedrock (USE_BEDROCK=true)
        api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
        vision_attrs: dict = {}
        if current_app.config.get("VISION_MODEL_ID"):
            from ..services.genai import vision_assist
            vision_attrs = vision_assist(api_key, filepath, mime_type)
            if vision_attrs:
                result["genai_vision"] = vision_attrs

        # ── Grounded context (CSV RAG-lite) ───────────────────────────────
        df = load_df(category)
        category_label = category_labels[category]

        # Enrich description with vision-extracted attributes
        enriched_desc = description
        if vision_attrs.get("fabric"):
            enriched_desc = (
                f"Fabric: {vision_attrs['fabric']}. "
                f"Palette: {vision_attrs.get('palette', '')}. "
                + enriched_desc
            ).strip()

        context = build_context(enriched_desc, price, category, category_label, df)
        result["grounding_context"] = context

        # ── GenAI Draft → Critic loop ─────────────────────────────────────
        if current_app.config.get("GENAI_ENABLED", True):
            from ..services.cache_service import cache_get, cache_set, make_analysis_key
            from ..services.safety import post_flight_clean, pre_flight_check

            cache_key = make_analysis_key(enriched_desc, price, category)
            cached = cache_get(cache_key)
            if cached:
                result.update(cached)
            else:
                ok, reason = pre_flight_check(description)
                if ok:
                    from ..services.genai import generate_grounded_tips
                    # API key is optional when using Bedrock
                    genai_result = generate_grounded_tips(
                        api_key=api_key,
                        context=context,
                        analysis_result=result,
                    )
                    if genai_result.get("genai_tips"):
                        genai_result["genai_tips"] = post_flight_clean(
                            genai_result["genai_tips"]
                        )
                    result.update(genai_result)
                    cache_set(cache_key, genai_result)
                else:
                    log.info("GenAI skipped (pre-flight): %s", reason)
                    result["genai_skip_reason"] = reason

        # ── Persist result ────────────────────────────────────────────────
        _persist_result(result, category, description, price, filename)

        log.info(
            "Analysis complete: %s [cat=%s score=%s genai=%s]",
            filename, category,
            result.get("total_score"),
            bool(result.get("genai_tips")),
        )
        return jsonify(result)

    except FileNotFoundError as exc:
        log.error("CSV not found: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except json.JSONDecodeError as exc:
        log.error("Failed to parse Claude response: %s", exc)
        return jsonify({"error": f"Failed to parse AI response: {exc}"}), 500
    except Exception:
        log.exception("Unexpected error during analysis")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# GET /analyze/stream  — SSE streaming of Draft tips
# ---------------------------------------------------------------------------

@analysis_bp.route("/analyze/stream", methods=["GET"])
@login_required
def analyze_stream():
    """Stream Draft tips as Server-Sent Events.

    Query params:
        description   — product description (required)
        price         — target price
        category      — saree|lehenga|salwar_suit|kurti (default: saree)
        total_score   — int score from a previous /analyze call
        classification — LAUNCH|MODIFY|DO NOT PRODUCE
    """
    description = request.args.get("description", "").strip()
    if not description:
        return jsonify({"error": "description is required"}), 400

    price = request.args.get("price", "")
    category = request.args.get("category", "saree").strip().lower()
    total_score = request.args.get("total_score", "50")
    classification = request.args.get("classification", "MODIFY")

    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    if category not in category_csv_map:
        category = "saree"

    # API key is optional when using Bedrock (USE_BEDROCK=true)
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    category_labels = current_app.config["CATEGORY_LABELS"]
    category_label = category_labels[category]

    try:
        df = load_df(category)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    context = build_context(description, price, category, category_label, df)
    analysis_stub = {
        "category": category_label,
        "classification": classification,
        "total_score": int(total_score) if total_score.isdigit() else 50,
    }

    from ..services.genai import draft_stream

    def generate():
        yield f"data: {json.dumps({'status': 'streaming'})}\n\n"
        for event in draft_stream(api_key, context, analysis_stub):
            yield event

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# POST /generate-mockup
# ---------------------------------------------------------------------------

@analysis_bp.route("/generate-mockup", methods=["POST"])
@login_required
def generate_mockup():
    """Generate a realistic mockup image from an uploaded sketch.

    Form fields:
        sketch      — image file (PNG, JPG, JPEG, WEBP) — required
        category    — saree | lehenga | salwar_suit | kurti — required
        description — optional free-text description
    """
    if "sketch" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["sketch"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, WEBP"}), 400

    category_csv_map = current_app.config["CATEGORY_CSV_MAP"]
    category = request.form.get("category", "saree").strip().lower()
    if category not in category_csv_map:
        return jsonify({
            "error": (
                f"Unknown category '{category}'. "
                f"Valid options: {', '.join(category_csv_map.keys())}"
            )
        }), 400

    description = request.form.get("description", "").strip()

    filename = secure_filename(file.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    try:
        from ..services.mockup_service import generate_mockup as _generate_mockup

        result = _generate_mockup(
            sketch_path=filepath,
            category=category,
            description=description,
            upload_folder=upload_folder,
        )
        log.info(
            "Mockup generated [cat=%s mockup=%s]",
            category, result.get("mockup_url"),
        )
        return jsonify(result)

    except TimeoutError as exc:
        log.error("Mockup generation timed out: %s", exc)
        return jsonify({"error": "Mockup generation timed out. Please try again."}), 504
    except RuntimeError as exc:
        log.error("Mockup generation error: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except Exception:
        log.exception("Unexpected error during mockup generation")
        return jsonify({"error": "Mockup generation failed. Please try again."}), 500


# ---------------------------------------------------------------------------
# Persistence helper
# ---------------------------------------------------------------------------

def _persist_result(
    result: dict,
    category: str,
    description: str,
    price: str,
    filename: str,
) -> None:
    try:
        data_dir = current_app.config["DATA_DIR"]
        results_path = os.path.join(data_dir, _RESULTS_FILE)
        file_exists = os.path.exists(results_path)
        row = {
            "id": uuid.uuid4().hex[:8],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "filename": filename,
            "description": (description or "")[:200],
            "price": price,
            "total_score": result.get("total_score", ""),
            "classification": result.get("classification", ""),
            "genai_tips": (result.get("genai_tips") or "")[:500],
            "genai_model": result.get("genai_model", ""),
            "genai_latency_ms": result.get("genai_latency_ms", ""),
            "genai_score": result.get("genai_score", ""),
        }
        with open(results_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_RESULTS_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as exc:
        log.warning("Failed to persist analysis result: %s", exc)
