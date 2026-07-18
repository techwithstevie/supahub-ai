from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models.schemas import ResumeRequest
from utils.github_fetcher import fetch_user_repos
from graph.pipeline import build_pipeline
import json

app = FastAPI(title="ResumeForge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = build_pipeline()

@app.post("/generate-resume")
async def generate_resume(request: ResumeRequest):
    try:
        github_data = await fetch_user_repos(request.github_username, request.github_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub fetch failed: {str(e)}")

    initial_state = {
        "raw_data": github_data,
        "skills": [],
        "experience_bullets": [],
        "resume_markdown": "",
        "target_role": request.target_role or "Software Engineer",
        "user_info": {
            "full_name": request.full_name or github_data["user"].get("name", ""),
            "email": request.email or github_data["user"].get("email", ""),
            "phone": request.phone or "",
            "username": request.github_username,
            "location": github_data["user"].get("location", ""),
        }
    }

    result = pipeline.invoke(initial_state)
    
    return {
        "resume_markdown": result["resume_markdown"],
        "skills": result["skills"],
        "projects": result["experience_bullets"],
        "agent_log": ["repo_analyst ✓", "skills_extractor ✓", "experience_writer ✓", "resume_assembler ✓"]
    }

@app.get("/health")
def health():
    return {"status": "ok", "model": "llama3.1"}