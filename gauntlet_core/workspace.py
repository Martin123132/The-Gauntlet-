from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os

from .models import AnalysisReport, analysis_report_from_dict
from .repair_workshop import normalize_repair_status
from .revision_recheck import RevisionRecheckResult, normalize_revision_rechecks, revision_recheck_counts


WORKSPACE_SCHEMA_VERSION = 3
WORKSPACE_ENV_VAR = "GAUNTLET_WORKSPACE_DIR"
DEFAULT_REVIEW_STATUS = "unreviewed"
REVIEW_STATUSES = ("unreviewed", "confirmed", "false-positive", "needs-follow-up")


@dataclass(frozen=True)
class SavedRunSummary:
    run_id: str
    source_name: str
    run_kind: str
    verdict: str
    confidence: float
    created_at: str
    saved_at: str
    claim_count: int
    finding_count: int
    evidence_score: float
    review_status: str = DEFAULT_REVIEW_STATUS
    notes: str = ""
    repair_progress_counts: dict[str, int] | None = None
    revision_recheck_counts: dict[str, int] | None = None


@dataclass(frozen=True)
class SavedRun:
    run_id: str
    run_kind: str
    saved_at: str
    report: AnalysisReport
    benchmark_metadata: dict[str, Any] | None = None
    review_status: str = DEFAULT_REVIEW_STATUS
    notes: str = ""
    repair_progress: dict[str, dict[str, str]] | None = None
    revision_rechecks: dict[str, dict[str, Any]] | None = None

    @property
    def summary(self) -> SavedRunSummary:
        return summarize_saved_run(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKSPACE_SCHEMA_VERSION,
            "run_id": self.run_id,
            "run_kind": self.run_kind,
            "saved_at": self.saved_at,
            "review_status": self.review_status,
            "notes": self.notes,
            "repair_progress": self.repair_progress or {},
            "revision_rechecks": self.revision_rechecks or {},
            "benchmark": self.benchmark_metadata,
            "report": self.report.to_dict(),
        }


def workspace_runs_dir() -> Path:
    configured = os.environ.get(WORKSPACE_ENV_VAR)
    if configured:
        return Path(configured)
    return Path.cwd() / ".gauntlet" / "workspace" / "runs"


def save_analysis_run(report: AnalysisReport, run_kind: str, benchmark_result: Any | None = None) -> SavedRun:
    saved_at = utc_now_iso()
    run_id = build_run_id(report, saved_at)
    saved_run = SavedRun(
        run_id=run_id,
        run_kind=run_kind,
        saved_at=saved_at,
        report=report,
        benchmark_metadata=benchmark_metadata_from_result(benchmark_result),
    )
    write_saved_run(saved_run)
    return saved_run


def list_saved_runs() -> list[SavedRunSummary]:
    summaries: list[SavedRunSummary] = []
    for path in sorted(workspace_runs_dir().glob("*.json")):
        try:
            payload = read_json(path)
            summaries.append(summary_from_payload(payload))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return sorted(summaries, key=lambda item: item.saved_at, reverse=True)


def load_saved_run(run_id: str) -> SavedRun:
    payload = read_json(run_path(run_id))
    report = analysis_report_from_dict(payload["report"])
    return SavedRun(
        run_id=payload.get("run_id", run_id),
        run_kind=payload.get("run_kind", "analysis"),
        saved_at=payload.get("saved_at", report.created_at),
        report=report,
        benchmark_metadata=payload.get("benchmark"),
        review_status=payload.get("review_status", DEFAULT_REVIEW_STATUS),
        notes=payload.get("notes", ""),
        repair_progress=normalize_repair_progress(payload.get("repair_progress", {})),
        revision_rechecks=normalize_revision_rechecks(payload.get("revision_rechecks", {})),
    )


def delete_saved_run(run_id: str) -> None:
    run_path(run_id).unlink(missing_ok=True)


def update_saved_run_notes(run_id: str, notes: str, review_status: str) -> SavedRun:
    saved_run = load_saved_run(run_id)
    normalized_status = review_status if review_status in REVIEW_STATUSES else DEFAULT_REVIEW_STATUS
    updated = SavedRun(
        run_id=saved_run.run_id,
        run_kind=saved_run.run_kind,
        saved_at=saved_run.saved_at,
        report=saved_run.report,
        benchmark_metadata=saved_run.benchmark_metadata,
        review_status=normalized_status,
        notes=notes,
        repair_progress=saved_run.repair_progress,
        revision_rechecks=saved_run.revision_rechecks,
    )
    write_saved_run(updated)
    return updated


def update_saved_run_repair_progress(run_id: str, step_id: str, status: str, reviewer_note: str) -> SavedRun:
    saved_run = load_saved_run(run_id)
    repair_progress = dict(saved_run.repair_progress or {})
    repair_progress[step_id] = {
        "status": normalize_repair_status(status),
        "reviewer_note": reviewer_note,
        "updated_at": utc_now_iso(),
    }
    updated = SavedRun(
        run_id=saved_run.run_id,
        run_kind=saved_run.run_kind,
        saved_at=saved_run.saved_at,
        report=saved_run.report,
        benchmark_metadata=saved_run.benchmark_metadata,
        review_status=saved_run.review_status,
        notes=saved_run.notes,
        repair_progress=repair_progress,
        revision_rechecks=saved_run.revision_rechecks,
    )
    write_saved_run(updated)
    return updated


def update_saved_run_revision_recheck(run_id: str, result: RevisionRecheckResult | dict[str, Any]) -> SavedRun:
    saved_run = load_saved_run(run_id)
    revision_rechecks = dict(saved_run.revision_rechecks or {})
    payload = result.to_dict() if isinstance(result, RevisionRecheckResult) else dict(result)
    step_id = str(payload.get("step_id", ""))
    if not step_id:
        raise ValueError("Revision re-check result must include a step_id.")
    revision_rechecks[step_id] = normalize_revision_rechecks({step_id: payload})[step_id]
    updated = SavedRun(
        run_id=saved_run.run_id,
        run_kind=saved_run.run_kind,
        saved_at=saved_run.saved_at,
        report=saved_run.report,
        benchmark_metadata=saved_run.benchmark_metadata,
        review_status=saved_run.review_status,
        notes=saved_run.notes,
        repair_progress=saved_run.repair_progress,
        revision_rechecks=revision_rechecks,
    )
    write_saved_run(updated)
    return updated


def summarize_saved_run(saved_run: SavedRun) -> SavedRunSummary:
    report = saved_run.report
    return SavedRunSummary(
        run_id=saved_run.run_id,
        source_name=report.source_name,
        run_kind=saved_run.run_kind,
        verdict=report.verdict,
        confidence=report.confidence,
        created_at=report.created_at,
        saved_at=saved_run.saved_at,
        claim_count=len(report.claims),
        finding_count=len(report.findings),
        evidence_score=report.evidence.score,
        review_status=saved_run.review_status,
        notes=saved_run.notes,
        repair_progress_counts=repair_progress_counts(saved_run.repair_progress or {}),
        revision_recheck_counts=revision_recheck_counts(saved_run.revision_rechecks or {}),
    )


def summary_from_payload(payload: dict[str, Any]) -> SavedRunSummary:
    report = payload.get("report", {})
    evidence = report.get("evidence", {})
    return SavedRunSummary(
        run_id=payload["run_id"],
        source_name=report.get("source_name", "paper"),
        run_kind=payload.get("run_kind", "analysis"),
        verdict=report.get("verdict", "FAILS"),
        confidence=float(report.get("confidence", 0.0)),
        created_at=report.get("created_at", ""),
        saved_at=payload.get("saved_at", ""),
        claim_count=len(report.get("claims", [])),
        finding_count=len(report.get("findings", [])),
        evidence_score=float(evidence.get("score", 0.0)),
        review_status=payload.get("review_status", DEFAULT_REVIEW_STATUS),
        notes=payload.get("notes", ""),
        repair_progress_counts=repair_progress_counts(normalize_repair_progress(payload.get("repair_progress", {}))),
        revision_recheck_counts=revision_recheck_counts(normalize_revision_rechecks(payload.get("revision_rechecks", {}))),
    )


def write_saved_run(saved_run: SavedRun) -> None:
    directory = workspace_runs_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = run_path(saved_run.run_id)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(saved_run.to_dict(), indent=2), encoding="utf-8")
    temp_path.replace(path)


def run_path(run_id: str) -> Path:
    safe_id = "".join(character for character in run_id if character.isalnum() or character in "-_")
    if not safe_id:
        raise ValueError("Saved run id cannot be empty.")
    return workspace_runs_dir() / f"{safe_id}.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_repair_progress(raw_progress: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw_progress, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for raw_step_id, raw_value in raw_progress.items():
        if not isinstance(raw_step_id, str) or not isinstance(raw_value, dict):
            continue
        normalized[raw_step_id] = {
            "status": normalize_repair_status(raw_value.get("status")),
            "reviewer_note": str(raw_value.get("reviewer_note", "")),
            "updated_at": str(raw_value.get("updated_at", "")),
        }
    return normalized


def repair_progress_counts(progress: dict[str, dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in progress.values():
        status = normalize_repair_status(item.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def build_run_id(report: AnalysisReport, saved_at: str) -> str:
    timestamp = saved_at.split("+", 1)[0].replace("-", "").replace(":", "").replace(".", "")
    digest = hashlib.sha256(f"{report.source_name}|{report.created_at}|{saved_at}".encode("utf-8")).hexdigest()[:8]
    return f"{timestamp}-{safe_stem(report.source_name)}-{digest}"


def safe_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in stem)
    return "-".join(part for part in cleaned.split("-") if part)[:60] or "paper"


def benchmark_metadata_from_result(benchmark_result: Any | None) -> dict[str, Any] | None:
    if benchmark_result is None:
        return None
    sample = getattr(benchmark_result, "sample", None)
    return {
        "sample_id": getattr(sample, "id", ""),
        "title": getattr(sample, "title", ""),
        "category": getattr(sample, "category", ""),
        "expected_verdict": getattr(sample, "expected_verdict", ""),
        "passed": bool(getattr(benchmark_result, "passed", False)),
        "score": float(getattr(benchmark_result, "score", 0.0)),
        "matched_findings": list(getattr(benchmark_result, "matched_findings", ())),
        "missed_findings": list(getattr(benchmark_result, "missed_findings", ())),
        "extra_findings": list(getattr(benchmark_result, "extra_findings", ())),
        "matched_claim_gaps": list(getattr(benchmark_result, "matched_claim_gaps", ())),
        "missed_claim_gaps": list(getattr(benchmark_result, "missed_claim_gaps", ())),
        "extra_claim_gaps": list(getattr(benchmark_result, "extra_claim_gaps", ())),
        "absent_findings_kept_out": list(getattr(benchmark_result, "absent_findings_kept_out", ())),
        "unexpected_absent_findings": list(getattr(benchmark_result, "unexpected_absent_findings", ())),
        "absent_claim_gaps_kept_out": list(getattr(benchmark_result, "absent_claim_gaps_kept_out", ())),
        "unexpected_absent_claim_gaps": list(getattr(benchmark_result, "unexpected_absent_claim_gaps", ())),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
