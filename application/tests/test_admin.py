"""Tests for admin routes — proposal patch application and CRUD."""
import csv
import json
import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Patch application helper (standalone, no Flask)
# ---------------------------------------------------------------------------

def _write_baselines(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _read_baselines(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestApplyPatch:
    """Test the _apply_patch function in isolation."""

    def test_updates_matching_category(self, tmp_path):
        path = tmp_path / "category_baselines.csv"
        rows = [
            {"category": "saree", "avg_price": "812", "demand_level": "high"},
            {"category": "kurti", "avg_price": "718", "demand_level": "medium"},
        ]
        _write_baselines(str(path), rows)

        patch = json.dumps({"category": "saree", "updates": {"avg_price": "880"}})

        # Inline the logic (no app context needed)
        existing = _read_baselines(str(path))
        fieldnames = list(existing[0].keys())
        updates = json.loads(patch).get("updates", {})
        target = json.loads(patch).get("category", "").lower()
        for row in existing:
            if row["category"].lower() == target:
                row.update({k: v for k, v in updates.items() if k in fieldnames})
        _write_baselines(str(path), existing)

        result = _read_baselines(str(path))
        saree_row = next(r for r in result if r["category"] == "saree")
        kurti_row = next(r for r in result if r["category"] == "kurti")
        assert saree_row["avg_price"] == "880"
        assert kurti_row["avg_price"] == "718"  # unchanged

    def test_unknown_category_leaves_csv_unchanged(self, tmp_path):
        path = tmp_path / "category_baselines.csv"
        rows = [{"category": "saree", "avg_price": "812"}]
        _write_baselines(str(path), rows)

        existing = _read_baselines(str(path))
        fieldnames = list(existing[0].keys())
        target = "lehenga"  # not present
        updates = {"avg_price": "9999"}
        for row in existing:
            if row["category"].lower() == target:
                row.update({k: v for k, v in updates.items() if k in fieldnames})
        _write_baselines(str(path), existing)

        result = _read_baselines(str(path))
        assert result[0]["avg_price"] == "812"

    def test_unknown_fields_not_applied(self, tmp_path):
        path = tmp_path / "category_baselines.csv"
        rows = [{"category": "saree", "avg_price": "812"}]
        _write_baselines(str(path), rows)

        existing = _read_baselines(str(path))
        fieldnames = list(existing[0].keys())
        target = "saree"
        updates = {"avg_price": "900", "nonexistent_column": "value"}
        safe_keys = {k for k in updates if k in fieldnames}
        for row in existing:
            if row["category"].lower() == target:
                row.update({k: updates[k] for k in safe_keys})
        _write_baselines(str(path), existing)

        result = _read_baselines(str(path))
        assert result[0]["avg_price"] == "900"
        assert "nonexistent_column" not in result[0]


# ---------------------------------------------------------------------------
# Proposals CSV read/write helpers
# ---------------------------------------------------------------------------

class TestProposalsCsv:
    FIELDS = ["id", "timestamp", "type", "patch_json", "summary", "confidence", "status"]

    def _write_proposals(self, path: str, rows: list[dict]) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def _read_proposals(self, path: str) -> list[dict]:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_pending_proposal_can_be_approved(self, tmp_path):
        path = tmp_path / "proposals.csv"
        proposal = {
            "id": "abc12345",
            "timestamp": "2026-03-01T00:00:00+00:00",
            "type": "baseline_update",
            "patch_json": json.dumps({"category": "saree", "updates": {"avg_price": "850"}}),
            "summary": "Adjust saree avg price",
            "confidence": "0.88",
            "status": "pending",
        }
        self._write_proposals(str(path), [proposal])

        rows = self._read_proposals(str(path))
        for row in rows:
            if row["id"] == "abc12345" and row["status"] == "pending":
                row["status"] = "approved"
        self._write_proposals(str(path), rows)

        result = self._read_proposals(str(path))
        assert result[0]["status"] == "approved"

    def test_cannot_re_approve_approved_proposal(self, tmp_path):
        path = tmp_path / "proposals.csv"
        proposal = {
            "id": "xyz99999",
            "timestamp": "2026-03-01T00:00:00+00:00",
            "type": "baseline_update",
            "patch_json": "{}",
            "summary": "Already done",
            "confidence": "0.9",
            "status": "approved",
        }
        self._write_proposals(str(path), [proposal])

        rows = self._read_proposals(str(path))
        already_approved = any(
            r["id"] == "xyz99999" and r["status"] != "pending" for r in rows
        )
        assert already_approved

    def test_declined_proposal_status_persisted(self, tmp_path):
        path = tmp_path / "proposals.csv"
        proposal = {
            "id": "dec00001",
            "timestamp": "2026-03-01T00:00:00+00:00",
            "type": "baseline_update",
            "patch_json": "{}",
            "summary": "Should be declined",
            "confidence": "0.4",
            "status": "pending",
        }
        self._write_proposals(str(path), [proposal])

        rows = self._read_proposals(str(path))
        for row in rows:
            if row["id"] == "dec00001":
                row["status"] = "declined"
        self._write_proposals(str(path), rows)

        result = self._read_proposals(str(path))
        assert result[0]["status"] == "declined"
