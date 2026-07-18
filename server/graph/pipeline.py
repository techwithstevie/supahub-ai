from __future__ import annotations

import json
from typing import Any

from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from config import settings
from models.schemas import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeDocument,
    SkillCategory,
)
from utils.resume_template import render_html, render_markdown

llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.25,
)


class ResumeState(TypedDict):
    raw_data: dict[str, Any]
    skills: dict[str, Any]
    experience_bullets: list[Any]
    draft: dict[str, Any]
    resume_doc: dict[str, Any]
    resume_html: str
    resume_markdown: str
    target_role: str
    user_info: dict[str, Any]


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
            line
            for line in cleaned.split("\n")
            if not line.strip().startswith("```")
        ]
        cleaned = "\n".join(lines).strip()
    # salvage first { ... } or [ ... ]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_c)
        end = cleaned.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return json.loads(cleaned)


def repo_analyst_node(state: ResumeState) -> ResumeState:
    repos = state["raw_data"].get("repos", [])
    prompt = f"""You are a senior technical recruiter. Analyze these GitHub repos for a professional resume.
Repos JSON:
{json.dumps(repos, indent=2)}

Return ONLY JSON:
{{
  "top_projects": [
    {{
      "name": "",
      "description": "",
      "languages": [],
      "topics": [],
      "stars": 0,
      "why_strong": "",
      "impact_hints": []
    }}
  ],
  "seniority_signal": "",
  "domains": []
}}
Pick at most 5 strongest non-toy projects. Prefer production-looking stacks."""
    try:
        analysis = _parse_json(_invoke_text(prompt))
        if not isinstance(analysis, dict):
            raise ValueError("bad analysis")
    except Exception:
        analysis = {
            "top_projects": repos[:5],
            "seniority_signal": "mid-senior",
            "domains": [],
        }
    state["raw_data"] = {**state["raw_data"], "analysis": analysis}
    return state


def skills_extractor_node(state: ResumeState) -> ResumeState:
    repos = state["raw_data"].get("repos", [])
    analysis = state["raw_data"].get("analysis", {})
    langs: set[str] = set()
    topics: set[str] = set()
    for repo in repos:
        langs.update(repo.get("languages") or [])
        topics.update(repo.get("topics") or [])

    prompt = f"""You write SKILLS sections for senior engineering resumes (ATS, one page feel).
Target role: {state["target_role"]}
Languages seen: {sorted(langs)}
Topics seen: {sorted(topics)}
Analysis: {json.dumps(analysis)[:3000]}

Return ONLY JSON with categories EXACTLY like a premium resume:
{{
  "headline_tech": ["React Native", "TypeScript", "Python", "..."],
  "skills": [
    {{"category": "Languages", "items": ["TypeScript", "JavaScript", "Python"]}},
    {{"category": "Mobile", "items": []}},
    {{"category": "AI & ML", "items": []}},
    {{"category": "Frontend", "items": []}},
    {{"category": "Backend", "items": []}},
    {{"category": "Databases", "items": []}},
    {{"category": "Tooling", "items": []}}
  ]
}}
Rules:
- Only real, credible skills inferred from evidence
- 4–12 items per category max; drop empty categories
- headline_tech: 5–8 flagship technologies for the title line
- No soft skills, no fluff"""
    try:
        parsed = _parse_json(_invoke_text(prompt))
        if not isinstance(parsed, dict):
            raise ValueError("bad skills")
        state["skills"] = parsed
    except Exception:
        state["skills"] = {
            "headline_tech": sorted(langs)[:8],
            "skills": [
                {"category": "Languages", "items": sorted(langs)},
                {"category": "Tooling", "items": sorted(topics)[:10]},
            ],
        }
    return state


def experience_writer_node(state: ResumeState) -> ResumeState:
    """Projects become PROJECTS; synthesize EXPERIENCE-style bullets from repo work."""
    analysis = state["raw_data"].get("analysis", {})
    top = analysis.get("top_projects") or state["raw_data"].get("repos", [])[:5]
    user = state["user_info"]
    role = state["target_role"]

    prompt = f"""You are an elite tech resume writer. Voice: confident, concise, senior IC.
Target role: {role}
Candidate: {user.get("full_name", "")}

GitHub project evidence:
{json.dumps(top, indent=2)[:8000]}

Return ONLY JSON:
{{
  "summary": "2-3 sentences, first person implied (no I), quantified where possible, like: Full-stack, mobile, and AI engineer with ...",
  "experience": [
    {{
      "company": "Derived from strongest project/org or 'Independent / Open Source'",
      "title": "{role}",
      "location": "Remote",
      "start": "YYYY or Mon YYYY",
      "end": "Present",
      "bullets": [
        "Built ...",
        "Engineered ...",
        "Improved ..."
      ]
    }}
  ],
  "projects": [
    {{
      "name": "ProjectName",
      "stack": ["Python", "Ollama"],
      "links": ["Code"],
      "bullets": [
        "Built ...",
        "Engineered ..."
      ]
    }}
  ]
}}

HARD RULES for bullets (match Fortune-500 / senior SWE resumes):
- Start with strong verbs: Built, Engineered, Architected, Delivered, Implemented, Optimized
- Specific tech + outcome; no generic "worked on"
- 1 line each, ~12–22 words
- 2–4 bullets per experience entry; 2–3 per project
- 2–4 experience entries max (group related work if needed)
- 3–5 projects max (best only)
- Never invent FAANG employers; if only GitHub, use honest labels (Contract / Independent / Open Source / Personal Product)
- summary: no first-person pronouns; quote-ready professional blurb"""
    try:
        parsed = _parse_json(_invoke_text(prompt))
        if not isinstance(parsed, dict):
            raise ValueError("bad exp")
        state["experience_bullets"] = parsed.get("experience") or []
        state["draft"] = parsed
    except Exception:
        state["experience_bullets"] = []
        state["draft"] = {
            "summary": f"{role} building production software from open-source and shipped projects.",
            "experience": [],
            "projects": [
                {
                    "name": p.get("name", "Project"),
                    "stack": p.get("languages") or [],
                    "links": ["Code"],
                    "bullets": [
                        p.get("description")
                        or f"Developed {p.get('name', 'project')} using modern tooling."
                    ],
                }
                for p in (top[:4] if isinstance(top, list) else [])
            ],
        }
    return state


def resume_assembler_node(state: ResumeState) -> ResumeState:
    user = state["user_info"]
    skills_payload = state.get("skills") or {}
    draft = state.get("draft") or {}

    # Optional LLM polish pass for summary only if thin
    summary = (draft.get("summary") or "").strip()
    if len(summary) < 40:
        summary = (
            f"{state['target_role']} with hands-on experience across full-stack, "
            f"mobile, and AI-integrated systems, shipping production-quality work "
            f"from real repositories and iterative delivery."
        )

    skill_cats = []
    for row in skills_payload.get("skills") or []:
        if isinstance(row, dict) and row.get("items"):
            skill_cats.append(
                SkillCategory(
                    category=str(row.get("category") or "Skills"),
                    items=[str(x) for x in row.get("items") or []],
                )
            )

    experience = []
    for row in draft.get("experience") or state.get("experience_bullets") or []:
        if not isinstance(row, dict):
            continue
        experience.append(
            ExperienceItem(
                company=str(row.get("company") or "Independent"),
                title=str(row.get("title") or state["target_role"]),
                location=str(row.get("location") or "Remote"),
                start=str(row.get("start") or ""),
                end=str(row.get("end") or "Present"),
                bullets=[str(b) for b in (row.get("bullets") or []) if b],
            )
        )

    projects = []
    for row in draft.get("projects") or []:
        if not isinstance(row, dict):
            continue
        projects.append(
            ProjectItem(
                name=str(row.get("name") or "Project"),
                stack=[str(s) for s in (row.get("stack") or [])],
                links=[str(l) for l in (row.get("links") or ["Code"])],
                bullets=[str(b) for b in (row.get("bullets") or []) if b],
            )
        )

    education = [
        EducationItem(
            school="Coding Temple",
            credential="Software Engineering Certificate",
        )
    ]
    # allow override from user_info later

    doc = ResumeDocument(
        full_name=str(user.get("full_name") or "Software Engineer"),
        phone=str(user.get("phone") or ""),
        email=str(user.get("email") or ""),
        linkedin=str(user.get("linkedin") or ""),
        github=str(
            user.get("github")
            or (
                f"https://github.com/{user.get('username')}"
                if user.get("username")
                else ""
            )
        ),
        portfolio=str(user.get("portfolio") or ""),
        target_title=str(state.get("target_role") or "Senior Software Engineer"),
        headline_tech=[
            str(t) for t in (skills_payload.get("headline_tech") or [])[:8]
        ],
        summary=summary,
        skills=skill_cats,
        experience=experience,
        projects=projects,
        education=education,
    )

    # Final structure enforcement via model_dump
    state["resume_doc"] = doc.model_dump()
    state["resume_html"] = render_html(doc)
    state["resume_markdown"] = render_markdown(doc)
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