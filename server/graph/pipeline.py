from __future__ import annotations

import json
from typing import Any

from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from config import settings

llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.3,
)


class ResumeState(TypedDict):
    raw_data: dict[str, Any]
    skills: dict[str, Any]
    experience_bullets: list[Any]
    resume_markdown: str
    target_role: str
    user_info: dict[str, Any]


def _invoke_text(prompt: str) -> str:
    """Normalize ChatOllama / message responses to a plain string."""
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
    """Strip optional markdown fences and parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def repo_analyst_node(state: ResumeState) -> ResumeState:
    repos = state["raw_data"].get("repos", [])
    repo_summary = json.dumps(repos, indent=2)
    prompt = f"""You are a senior technical recruiter analyst. Analyze these GitHub repositories
and extract key technical insights. Focus on: complexity, tech stack depth,
real-world applicability, and project quality.

Repos: {repo_summary}

Return a JSON object with: {{ "top_projects": [...], "tech_depth": "..." }}
Return ONLY valid JSON, no extra text."""
    result = _invoke_text(prompt)
    try:
        analysis = _parse_json(result)
        if not isinstance(analysis, dict):
            raise ValueError("analysis must be an object")
    except Exception:
        analysis = {"top_projects": repos[:5], "tech_depth": "Full-stack"}

    state["raw_data"] = {**state["raw_data"], "analysis": analysis}
    return state


def skills_extractor_node(state: ResumeState) -> ResumeState:
    repos = state["raw_data"].get("repos", [])
    all_langs: set[str] = set()
    all_topics: set[str] = set()
    for repo in repos:
        all_langs.update(repo.get("languages", []) or [])
        all_topics.update(repo.get("topics", []) or [])

    prompt = f"""You are a technical skills analyst. Based on these languages and topics from a
developer's GitHub, build a comprehensive, recruiter-optimized skills section.

Languages found: {list(all_langs)}
Topics/Frameworks: {list(all_topics)}
Target Role: {state["target_role"]}

Return JSON: {{ "technical_skills": [...], "frameworks": [...], "tools": [...] }}
Return ONLY valid JSON."""
    result = _invoke_text(prompt)
    try:
        parsed = _parse_json(result)
        if not isinstance(parsed, dict):
            raise ValueError("skills payload must be an object")
        state["skills"] = parsed
    except Exception:
        state["skills"] = {
            "technical_skills": list(all_langs),
            "frameworks": list(all_topics),
            "tools": [],
        }
    return state


def experience_writer_node(state: ResumeState) -> ResumeState:
    analysis = state["raw_data"].get("analysis", {})
    top_projects = analysis.get(
        "top_projects", state["raw_data"].get("repos", [])[:5]
    )

    prompt = f"""You are an expert resume writer specializing in tech roles. Convert these GitHub
projects into powerful, STAR-method resume bullet points. Use action verbs,
quantify impact where possible, and target: {state["target_role"]}.

Projects: {json.dumps(top_projects, indent=2)}

Return JSON array: [{{"project": "name", "bullets": ["Built...", "Engineered..."]}}]
Return ONLY valid JSON."""
    result = _invoke_text(prompt)
    try:
        parsed = _parse_json(result)
        if not isinstance(parsed, list):
            raise ValueError("experience bullets must be an array")
        state["experience_bullets"] = parsed
    except Exception:
        state["experience_bullets"] = []
    return state


def resume_assembler_node(state: ResumeState) -> ResumeState:
    user = state["user_info"]
    skills = state["skills"]
    bullets = state["experience_bullets"]

    prompt = f"""You are a professional resume designer. Assemble a complete, ATS-optimized resume
in clean Markdown. Make it look polished, recruiter-ready, and tailored for: {state["target_role"]}.

Candidate Info:
- Name: {user.get("full_name", user.get("name", "Developer"))}
- Email: {user.get("email", "")}
- Phone: {user.get("phone", "")}
- GitHub: https://github.com/{user.get("username", "")}
- Location: {user.get("location", "")}

Skills: {json.dumps(skills, indent=2)}
Project Experience: {json.dumps(bullets, indent=2)}

Format sections: Summary | Technical Skills | Projects | Education (placeholder)
Use clean Markdown with proper headers. Make it EXCEPTIONAL.
Return ONLY the markdown resume, no commentary."""
    state["resume_markdown"] = _invoke_text(prompt)
    return state


def build_pipeline():
    graph = StateGraph(ResumeState)
    graph.add_node("repo_analyst", repo_analyst_node)
    graph.add_node("skills_extractor", skills_extractor_node)
    graph.add_node("experience_writer", experience_writer_node)
    graph.add_node("resume_assembler", resume_assembler_node)

    graph.set_entry_point("repo_analyst")
    graph.add_edge("repo_analyst", "skills_extractor")
    graph.add_edge("skills_extractor", "experience_writer")
    graph.add_edge("experience_writer", "resume_assembler")
    graph.add_edge("resume_assembler", END)

    return graph.compile()