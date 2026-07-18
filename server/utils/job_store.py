from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from models.job_schemas import (
    FunnelMetrics,
    JobApplication,
    JobApplicationCreate,
    JobApplicationUpdate,
    JobStage,
)

_LOCK = threading.Lock()
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "job_applications.json"

# Stages that mean "we applied / in process from apply"
_APPLIED_STAGES = {
    JobStage.applied,
    JobStage.screening,
    JobStage.interview,
    JobStage.offer,
    JobStage.accepted,
    JobStage.rejected,
    JobStage.ghosted,
    JobStage.withdrawn,
}
_RESPONSE_STAGES = {
    JobStage.screening,
    JobStage.interview,
    JobStage.offer,
    JobStage.accepted,
    JobStage.rejected,
}
_INTERVIEW_STAGES = {
    JobStage.interview,
    JobStage.offer,
    JobStage.accepted,
}
_OFFER_STAGES = {JobStage.offer, JobStage.accepted}


def _ensure_file() -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _DATA_PATH.exists():
        _DATA_PATH.write_text("[]", encoding="utf-8")


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    raise TypeError(type(obj))


def _load() -> list[dict[str, Any]]:
    _ensure_file()
    raw = _DATA_PATH.read_text(encoding="utf-8").strip() or "[]"
    data = json.loads(raw)
    return data if isinstance(data, list) else []


def _save(rows: list[dict[str, Any]]) -> None:
    _ensure_file()
    _DATA_PATH.write_text(
        json.dumps(rows, indent=2, default=str),
        encoding="utf-8",
    )


def list_applications() -> list[JobApplication]:
    with _LOCK:
        return [JobApplication.model_validate(r) for r in _load()]


def create_application(payload: JobApplicationCreate) -> JobApplication:
    data = payload.model_dump()
    now = datetime.utcnow()
    if data.get("applied_at") is None:
        data["applied_at"] = now
    if data.get("applied_date") is None and data.get("stage") != JobStage.saved:
        data["applied_date"] = (
            data["applied_at"].date()
            if isinstance(data["applied_at"], datetime)
            else date.today()
        )
    app = JobApplication(
        id=str(uuid4()),
        created_at=now,
        updated_at=now,
        **data,
    )
    with _LOCK:
        rows = _load()
        rows.append(app.model_dump(mode="json"))
        _save(rows)
    return app


def update_application(app_id: str, payload: JobApplicationUpdate) -> JobApplication:
    with _LOCK:
        rows = _load()
        idx = next((i for i, r in enumerate(rows) if r.get("id") == app_id), None)
        if idx is None:
            raise KeyError(app_id)
        current = JobApplication.model_validate(rows[idx])
        data = current.model_dump()
        patch = payload.model_dump(exclude_unset=True)
        data.update(patch)
        data["updated_at"] = datetime.utcnow().isoformat()
        updated = JobApplication.model_validate(data)
        rows[idx] = updated.model_dump(mode="json")
        _save(rows)
        return updated


def delete_application(app_id: str) -> None:
    with _LOCK:
        rows = _load()
        new_rows = [r for r in rows if r.get("id") != app_id]
        if len(new_rows) == len(rows):
            raise KeyError(app_id)
        _save(new_rows)


def _rate(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round(100.0 * n / d, 1)


def compute_metrics(apps: list[JobApplication] | None = None) -> FunnelMetrics:
    apps = apps if apps is not None else list_applications()
    by_stage: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for a in apps:
        by_stage[a.stage.value] = by_stage.get(a.stage.value, 0) + 1
        by_source[a.source.value] = by_source.get(a.source.value, 0) + 1

    applied = [a for a in apps if a.stage in _APPLIED_STAGES or a.applied_date]
    # count distinct apply attempts: everything except pure "saved"
    applied_list = [a for a in apps if a.stage != JobStage.saved]
    applied_count = len(applied_list)

    response_count = sum(1 for a in apps if a.stage in _RESPONSE_STAGES)
    interview_count = sum(1 for a in apps if a.stage in _INTERVIEW_STAGES)
    offer_count = sum(1 for a in apps if a.stage in _OFFER_STAGES)
    rejected_count = sum(1 for a in apps if a.stage == JobStage.rejected)
    ghosted_count = sum(1 for a in apps if a.stage == JobStage.ghosted)

    tailored = [a for a in applied_list if a.tailored]
    untailored = [a for a in applied_list if not a.tailored]
    referral = [a for a in applied_list if a.referral]
    cold = [a for a in applied_list if not a.referral]

    def iv_rate(subset: list[JobApplication]) -> float:
        if not subset:
            return 0.0
        hits = sum(1 for a in subset if a.stage in _INTERVIEW_STAGES)
        return _rate(hits, len(subset))

    # avg days since applied
    days: list[float] = []
    today = date.today()
    for a in applied_list:
        if a.applied_date:
            days.append(float((today - a.applied_date).days))
    avg_days = round(sum(days) / len(days), 1) if days else 0.0

    # crude rejection themes from free text
    themes: dict[str, int] = {}
    keywords = [
        "experience",
        "overqualified",
        "underqualified",
        "salary",
        "location",
        "sponsorship",
        "clearance",
        "stack",
        "culture",
        "timing",
        "headcount",
        "ghost",
    ]
    for a in apps:
        text = f"{a.rejection_reason} {a.notes}".lower()
        for kw in keywords:
            if kw in text:
                themes[kw] = themes.get(kw, 0) + 1
    top_themes = [
        k for k, _ in sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return FunnelMetrics(
        total=len(apps),
        by_stage=by_stage,
        by_source=by_source,
        applied_count=applied_count,
        response_count=response_count,
        interview_count=interview_count,
        offer_count=offer_count,
        rejected_count=rejected_count,
        ghosted_count=ghosted_count,
        tailored_count=len(tailored),
        referral_count=len(referral),
        response_rate=_rate(response_count, applied_count),
        interview_rate=_rate(interview_count, applied_count),
        offer_rate=_rate(offer_count, applied_count),
        ghost_rate=_rate(ghosted_count, applied_count),
        tailored_interview_rate=iv_rate(tailored),
        untailored_interview_rate=iv_rate(untailored),
        referral_interview_rate=iv_rate(referral),
        cold_interview_rate=iv_rate(cold),
        avg_days_in_pipeline=avg_days,
        top_rejection_themes=top_themes,
    )