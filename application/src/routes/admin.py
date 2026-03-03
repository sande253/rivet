"""Admin routes — AI Proposals management.

Endpoints
---------
GET  /admin/               — admin UI page
GET  /admin/proposals      — list all proposals (JSON)
POST /admin/proposals/<id>/approve  — apply patch + mark approved
POST /admin/proposals/<id>/decline  — mark declined
POST /admin/proposals/generate      — run optimizer, produce new proposals

Proposals are stored in data/ai_proposals.csv.
Category baselines are stored in data/category_baselines.csv.
"""
import csv
import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
log = logging.getLogger(__name__)

_PROPOSALS_FILE = "ai_proposals.csv"
_BASELINES_FILE = "category_baselines.csv"
_PROPOSALS_FIELDS = [
    "id", "timestamp", "type", "patch_json",
    "summary", "confidence", "status",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proposals_path() -> str:
    return os.path.join(current_app.config["DATA_DIR"], _PROPOSALS_FILE)


def _baselines_path() -> str:
    return os.path.join(current_app.config["DATA_DIR"], _BASELINES_FILE)


def _read_proposals() -> list[dict]:
    path = _proposals_path()
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_proposals(rows: list[dict]) -> None:
    path = _proposals_path()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_PROPOSALS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _apply_patch(patch_json: str) -> None:
    """Apply a safe baseline patch to category_baselines.csv.

    patch_json schema:
        {"category": "saree", "updates": {"avg_price": "850", ...}}
    """
    patch = json.loads(patch_json)
    path = _baselines_path()

    if not os.path.exists(path):
        log.warning("category_baselines.csv not found — patch skipped")
        return

    # Backup before modifying
    ts = int(datetime.now().timestamp())
    backup = path.replace(".csv", f"_backup_{ts}.csv")
    shutil.copy2(path, backup)
    log.info("Backed up baselines → %s", backup)

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        log.warning("category_baselines.csv is empty — nothing to patch")
        return

    fieldnames = list(rows[0].keys())
    target_cat = patch.get("category", "").lower()
    updates: dict = patch.get("updates", {})

    # Only allow updating fields that already exist in the CSV
    safe_keys = {k for k in updates if k in fieldnames}
    if not safe_keys:
        log.warning("No safe fields to update in patch: %s", patch)
        return

    for row in rows:
        if row.get("category", "").lower() == target_cat:
            for k in safe_keys:
                row[k] = updates[k]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info("Applied baseline patch category=%s keys=%s", target_cat, list(safe_keys))


def _run_optimizer(api_key: str, data_dir: str) -> list[dict]:
    """Generate AI-proposed baseline edits.  Does NOT auto-apply."""
    import anthropic

    baselines_path = os.path.join(data_dir, _BASELINES_FILE)
    if not os.path.exists(baselines_path):
        return []

    with open(baselines_path, encoding="utf-8") as f:
        baselines_text = f.read()

    prompt = (
        "You are a market data analyst for an Indian ethnic wear platform.\n\n"
        "CURRENT CATEGORY BASELINES (CSV):\n"
        f"{baselines_text}\n\n"
        "Propose up to 3 safe, data-driven edits to these baselines "
        "(e.g. adjusting avg_price based on market shifts).\n\n"
        "Respond ONLY with a JSON array (no markdown):\n"
        '[\n'
        '  {\n'
        '    "type": "baseline_update",\n'
        '    "summary": "one-line description",\n'
        '    "confidence": 0.85,\n'
        '    "patch_json": {"category":"saree","updates":{"avg_price":"880"}}\n'
        '  }\n'
        ']'
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=os.environ.get("CRITIC_MODEL_ID", "claude-sonnet-4-6"),
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()

    proposals_data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in proposals_data:
        rows.append(
            {
                "id": uuid.uuid4().hex[:8],
                "timestamp": now,
                "type": item.get("type", "baseline_update"),
                "patch_json": json.dumps(item.get("patch_json", {})),
                "summary": item.get("summary", ""),
                "confidence": str(item.get("confidence", "")),
                "status": "pending",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@admin_bp.route("/", methods=["GET"])
@login_required
def admin_ui():
    return render_template("admin.html")


@admin_bp.route("/proposals", methods=["GET"])
@login_required
def list_proposals():
    proposals = _read_proposals()
    return jsonify({"proposals": proposals, "count": len(proposals)})


@admin_bp.route("/proposals/generate", methods=["POST"])
@login_required
def generate_proposals():
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 500
    try:
        new_rows = _run_optimizer(api_key, current_app.config["DATA_DIR"])
        existing = _read_proposals()
        existing.extend(new_rows)
        _write_proposals(existing)
        return jsonify({"generated": len(new_rows), "proposals": new_rows})
    except Exception as exc:
        log.error("Optimizer failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@admin_bp.route("/proposals/<proposal_id>/approve", methods=["POST"])
@login_required
def approve_proposal(proposal_id: str):
    proposals = _read_proposals()
    found = False
    for row in proposals:
        if row["id"] == proposal_id:
            if row["status"] != "pending":
                return (
                    jsonify({"error": f"Proposal {proposal_id} is already {row['status']}"}),
                    400,
                )
            try:
                _apply_patch(row["patch_json"])
            except Exception as exc:
                log.error("Patch apply failed for %s: %s", proposal_id, exc)
                return jsonify({"error": f"Patch apply failed: {exc}"}), 500
            row["status"] = "approved"
            row["timestamp"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        return jsonify({"error": f"Proposal {proposal_id} not found"}), 404
    _write_proposals(proposals)
    log.info("Proposal %s approved", proposal_id)
    return jsonify({"status": "approved", "id": proposal_id})


@admin_bp.route("/proposals/<proposal_id>/decline", methods=["POST"])
@login_required
def decline_proposal(proposal_id: str):
    proposals = _read_proposals()
    found = False
    for row in proposals:
        if row["id"] == proposal_id:
            if row["status"] != "pending":
                return (
                    jsonify({"error": f"Proposal {proposal_id} is already {row['status']}"}),
                    400,
                )
            row["status"] = "declined"
            found = True
            break
    if not found:
        return jsonify({"error": f"Proposal {proposal_id} not found"}), 404
    _write_proposals(proposals)
    log.info("Proposal %s declined", proposal_id)
    return jsonify({"status": "declined", "id": proposal_id})
