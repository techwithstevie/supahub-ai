from __future__ import annotations

import json
from typing import Any

from langchain_ollama import ChatOllama

from config import settings
from models.job_schemas import (
    AnalyzeJobSearchResponse,
    FunnelMetrics,
    HiringTeamMember,
    JobApplication,
)

llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.35,
)


def _invoke_text(prompt: str) -> str:
    msg = llm.invoke(prompt)
    if isinstance(msg, str):
        return msg
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(msg)


def _parse_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [
            ln for ln in cleaned.split("\n") if not ln.strip().startswith("```")
        ]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])
    return json.loads(cleaned)


def _hiring_team_payload(app: JobApplication) -> list[dict[str, str]]:
    details = app.linkedin_details
    if not details:
        return [{"name": "N/A", "title": "N/A", "profile_url": ""}]

    team = details.hiring_team or []
    if not team:
        return [{"name": "N/A", "title": "N/A", "profile_url": ""}]

    out: list[dict[str, str]] = []
    for person in team:
        if isinstance(person, HiringTeamMember):
            out.append(
                {
                    "name": person.name or "N/A",
                    "title": person.title or "N/A",
                    "profile_url": person.profile_url or "",
                    "connection_degree": person.connection_degree or "",
                    "extra": person.extra or "",
                }
            )
        elif isinstance(person, dict):
            out.append(
                {
                    "name": str(person.get("name") or "N/A"),
                    "title": str(person.get("title") or "N/A"),
                    "profile_url": str(person.get("profile_url") or ""),
                    "connection_degree": str(person.get("connection_degree") or ""),
                    "extra": str(person.get("extra") or ""),
                }
            )
    return out or [{"name": "N/A", "title": "N/A", "profile_url": ""}]


def _linkedin_payload(app: JobApplication) -> dict[str, Any] | None:
    d = app.linkedin_details
    if not d:
        return None
    return {
        "compensation": d.compensation or "N/A",
        "location": d.location or "N/A",
        "primary_responsibilities": (d.primary_responsibilities or "N/A")[:800],
        "candidate_qualifications": (d.candidate_qualifications or "N/A")[:800],
        "why_join": (d.why_join or "N/A")[:400],
        "about_company": (d.about_company or "N/A")[:400],
        "benefits": (d.benefits or "N/A")[:400],
        "requirements_added_by_poster": (
            d.requirements_added_by_poster or "N/A"
        )[:400],
        "hiring_team": _hiring_team_payload(app),
    }


def analyze_job_search(
    metrics: FunnelMetrics,
    applications: list[JobApplication],
    focus: str = "",
    include_notes: bool = True,
) -> AnalyzeJobSearchResponse:
    sample: list[dict[str, Any]] = []
    for a in applications[:40]:
        row: dict[str, Any] = {
            "company": a.company,
            "role": a.role_title,
            "stage": a.stage.value if hasattr(a.stage, "value") else str(a.stage),
            "source": a.source.value if hasattr(a.source, "value") else str(a.source),
            "tailored": a.tailored,
            "referral": a.referral,
            "target_role": a.resume_target_role,
            "rejection_reason": a.rejection_reason,
            "job_url": a.job_url,
        }
        if include_notes:
            row["notes"] = (a.notes or "")[:500]

        linkedin = _linkedin_payload(a)
        if linkedin:
            row["linkedin"] = linkedin

        sample.append(row)

    prompt = f"""You are a brutal but constructive career coach and recruiting analyst.
The candidate is a full-stack / mobile / AI engineer struggling to land interviews.
Applications are primarily from LinkedIn.

Use ONLY the metrics and application log below. Be specific and actionable.
Do not invent companies, hiring managers, or stats that are not in the data.

When a row includes a "linkedin" object, treat it as structured job-post data from
LinkedIn "About the job" and "Meet the hiring team":
- compensation
- location
- primary_responsibilities
- candidate_qualifications
- why_join (Why Join This Opportunity)
- about_company
- benefits (Benefits found in job post)
- requirements_added_by_poster (Requirements added by the job poster)
- hiring_team (name, title, profile_url; use N/A if none listed)

Judge resume/target-role fit against:
1) candidate_qualifications
2) requirements_added_by_poster
3) primary_responsibilities

If hiring_team names are not N/A, recommend concrete outreach to those people.
If hiring_team is N/A, say so and suggest alternate LinkedIn outreach (recruiters, employees at company).

METRICS JSON:
{metrics.model_dump_json(indent=2)}

APPLICATION SAMPLE (up to 40):
{json.dumps(sample, indent=2)}

USER FOCUS (optional):
{focus or "Why am I not getting interviews and what should I change this week?"}

Return ONLY JSON:
{{
  "diagnosis": "2-4 sentence plain-English diagnosis",
  "root_causes": ["cause 1", "cause 2", "cause 3"],
  "strengths": ["what is working"],
  "action_plan": ["this week action 1", "action 2", "action 3", "action 4"],
  "resume_recommendations": ["resume change 1", "resume change 2"],
  "outreach_recommendations": ["outreach change 1", "outreach change 2"],
  "priority_score": {{
    "resume_quality": 0,
    "targeting": 0,
    "volume": 0,
    "tailoring": 0,
    "networking": 0,
    "follow_up": 0
  }}
}}

priority_score values 0-100 (100 = strong / not the bottleneck).
If applied_count is low, call out volume.
If response_rate is low, call out resume/targeting vs LinkedIn qualifications.
If tailored_interview_rate >> untailored, push tailoring to each post's qualifications.
If referral_interview_rate is higher, push networking and hiring-team outreach.
Never invent FAANG employers or fake hiring-team contacts.
"""

    try:
        raw = _parse_json(_invoke_text(prompt))
        if not isinstance(raw, dict):
            raise ValueError("bad agent payload")
    except Exception as exc:
        raw = {
            "diagnosis": (
                f"Could not complete full AI analysis ({exc}). "
                f"Based on metrics alone: {metrics.applied_count} applications, "
                f"{metrics.interview_rate}% interview rate, "
                f"{metrics.response_rate}% response rate."
            ),
            "root_causes": [
                "Insufficient structured data or model parse failure",
                "Review response_rate and interview_rate manually",
                "Confirm LinkedIn job sections were captured on each application",
            ],
            "strengths": [],
            "action_plan": [
                "Log every LinkedIn application with Fetch details from URL",
                "Mark tailored vs cold applies against Candidate Qualifications",
                "Message Meet the hiring team when names are not N/A",
                "Re-run analysis after 10+ applications",
            ],
            "resume_recommendations": [
                "Mirror language from Candidate Qualifications and "
                "Requirements added by the job poster on each target role"
            ],
            "outreach_recommendations": [
                "When hiring_team is present, send a short note referencing "
                "one Primary Responsibility from the post",
                "When hiring_team is N/A, find a recruiter or engineer at the company on LinkedIn",
            ],
            "priority_score": {
                "resume_quality": 50,
                "targeting": 50,
                "volume": 50,
                "tailoring": 50,
                "networking": 50,
                "follow_up": 50,
            },
        }

    def _list(key: str) -> list[str]:
        val = raw.get(key) or []
        if not isinstance(val, list):
            return []
        return [str(x) for x in val]

    scores = raw.get("priority_score") or {}
    if not isinstance(scores, dict):
        scores = {}
    priority: dict[str, int] = {}
    for k, v in scores.items():
        try:
            priority[str(k)] = int(v)
        except (TypeError, ValueError):
            continue

    return AnalyzeJobSearchResponse(
        metrics=metrics,
        diagnosis=str(raw.get("diagnosis") or ""),
        root_causes=_list("root_causes"),
        strengths=_list("strengths"),
        action_plan=_list("action_plan"),
        resume_recommendations=_list("resume_recommendations"),
        outreach_recommendations=_list("outreach_recommendations"),
        priority_score=priority,
        raw_agent_json=raw if isinstance(raw, dict) else {},
        agent_log=["job_search_analyst ✓"],
    )