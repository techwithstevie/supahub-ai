from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from config import settings
from graph.pipeline import ResumeState, build_pipeline
from models.schemas import ResumeDocument, ResumeRequest, ResumeResponse
from utils.github_fetcher import fetch_user_repos

app = FastAPI(title="SupaHub AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = build_pipeline()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": settings.ollama_model,
        "ollama_base_url": settings.ollama_base_url,
    }


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
        resume_html=result.get("resume_html") or "",
        resume_markdown=result.get("resume_markdown") or "",
        raw_skills=result.get("skills") or {},
        agent_log=[
            "repo_analyst ✓",
            "skills_extractor ✓",
            "experience_writer ✓",
            "resume_assembler ✓",
        ],
    )


@app.post("/generate-resume/html", response_class=HTMLResponse)
async def generate_resume_html(request: ResumeRequest) -> HTMLResponse:
    payload = await generate_resume(request)
    return HTMLResponse(content=payload.resume_html)