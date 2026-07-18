from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import settings
from graph.job_analyst import analyze_job_search
from graph.pipeline import ResumeState, build_pipeline
from graph.section_refiner import refine_section

from models.job_schemas import (
    AnalyzeJobSearchRequest,
    AnalyzeJobSearchResponse,
    JobApplication,
    JobApplicationCreate,
    JobApplicationUpdate,
    JobMetricsResponse,
    ParseJobUrlRequest,
    ParseJobUrlResponse,
)

from models.schemas import (
    RefineSectionRequest,
    RenderedResumeResponse,
    ResumeDocument,
    ResumeRequest,
    ResumeResponse,
    UpdateResumeRequest,
)
from utils import job_store
from utils.github_fetcher import fetch_user_repos
from utils.resume_template import render_html, render_markdown
from utils.job_url_parser import parse_job_url

app = FastAPI(title="SupaHub AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = build_pipeline()


def _render(doc: ResumeDocument) -> RenderedResumeResponse:
    return RenderedResumeResponse(
        resume=doc,
        resume_html=render_html(doc),
        resume_markdown=render_markdown(doc),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": settings.ollama_model,
        "ollama_base_url": settings.ollama_base_url,
    }


# ── Resume ──────────────────────────────────────────────


@app.post("/generate-resume", response_model=ResumeResponse)
async def generate_resume(request: ResumeRequest) -> ResumeResponse:
    try:
        github_data = await fetch_user_repos(
            request.github_username,
            request.github_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub fetch failed: {exc}",
        ) from exc

    user: dict[str, Any] = github_data.get("user") or {}

    initial_state: ResumeState = {
        "raw_data": github_data,
        "skills": {},
        "experience_bullets": [],
        "draft": {},
        "resume_doc": {},
        "resume_html": "",
        "resume_markdown": "",
        "target_role": request.target_role or "Senior Software Engineer",
        "user_info": {
            "full_name": request.full_name or user.get("name") or "",
            "email": request.email or user.get("email") or "",
            "phone": request.phone or "",
            "linkedin": request.linkedin or "",
            "portfolio": request.portfolio or user.get("blog") or "",
            "username": request.github_username,
            "github": f"https://github.com/{request.github_username}",
            "location": request.location or user.get("location") or "",
        },
    }

    try:
        result = cast(ResumeState, pipeline.invoke(initial_state))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline failed: {exc}",
        ) from exc

    doc = ResumeDocument.model_validate(result.get("resume_doc") or {})

    return ResumeResponse(
        resume=doc,
        resume_html=result.get("resume_html") or render_html(doc),
        resume_markdown=result.get("resume_markdown") or render_markdown(doc),
        raw_skills=result.get("skills") or {},
        agent_log=[
            "repo_analyst ✓",
            "skills_extractor ✓",
            "experience_writer ✓",
            "resume_assembler ✓",
        ],
    )


@app.post("/refine-section", response_model=RenderedResumeResponse)
async def refine_resume_section(
    request: RefineSectionRequest,
) -> RenderedResumeResponse:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    try:
        updated = refine_section(request.resume, request.section, prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Section refine failed: {exc}",
        ) from exc
    out = _render(updated)
    out.agent_log = [f"refine:{request.section.value} ✓"]
    return out


@app.post("/update-resume", response_model=RenderedResumeResponse)
async def update_resume(request: UpdateResumeRequest) -> RenderedResumeResponse:
    try:
        doc = ResumeDocument.model_validate(request.resume.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid resume: {exc}") from exc
    out = _render(doc)
    out.agent_log = ["manual_update ✓"]
    return out


@app.post("/generate-resume/html", response_class=HTMLResponse)
async def generate_resume_html(request: ResumeRequest) -> HTMLResponse:
    payload = await generate_resume(request)
    return HTMLResponse(content=payload.resume_html)


# ── Job tracker ─────────────────────────────────────────


@app.get("/jobs/metrics", response_model=JobMetricsResponse)
def get_job_metrics() -> JobMetricsResponse:
    apps = job_store.list_applications()
    metrics = job_store.compute_metrics(apps)
    return JobMetricsResponse(
        metrics=metrics,
        applications=apps,
        insights_ready=metrics.applied_count >= 3,
    )


@app.post("/jobs/analyze", response_model=AnalyzeJobSearchResponse)
def post_job_analyze(payload: AnalyzeJobSearchRequest) -> AnalyzeJobSearchResponse:
    apps = job_store.list_applications()
    metrics = job_store.compute_metrics(apps)
    if metrics.total == 0:
        raise HTTPException(
            status_code=400,
            detail="Add job applications before running analysis",
        )
    return analyze_job_search(
        metrics=metrics,
        applications=apps,
        focus=payload.focus,
        include_notes=payload.include_notes,
    )


@app.get("/jobs", response_model=list[JobApplication])
def get_jobs() -> list[JobApplication]:
    return job_store.list_applications()


@app.post("/jobs", response_model=JobApplication)
def post_job(payload: JobApplicationCreate) -> JobApplication:
    return job_store.create_application(payload)


@app.patch("/jobs/{job_id}", response_model=JobApplication)
def patch_job(job_id: str, payload: JobApplicationUpdate) -> JobApplication:
    try:
        return job_store.update_application(job_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Application not found") from exc


@app.delete("/jobs/{job_id}")
def remove_job(job_id: str) -> dict[str, bool]:
    try:
        job_store.delete_application(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Application not found") from exc
    return {"ok": True}

@app.post("/jobs/parse-url", response_model=ParseJobUrlResponse)
async def parse_job_posting_url(payload: ParseJobUrlRequest) -> ParseJobUrlResponse:
    try:
        return await parse_job_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse job URL: {exc}",
        ) from exc