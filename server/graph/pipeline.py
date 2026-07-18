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
    ProjectLink,
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
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_c)
        end = cleaned.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return json.loads(cleaned)


def _repo_url_map(raw_data: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for repo in raw_data.get("repos") or []:
        name = str(repo.get("name") or "").lower()
        url = str(repo.get("url") or "")
        if name and url:
            mapping[name] = url
    return mapping


def _normalize_project_links(row: dict[str, Any], repo_map: dict[str, str]) -> list[ProjectLink]:
    links: list[ProjectLink] = []
    name = str(row.get("name") or "")
    repo = str(
        row.get("repo_url")
        or row.get("url")
        or row.get("html_url")
        or repo_map.get(name.lower())
        or ""
    )

    raw_links = row.get("links") or []
    if isinstance(raw_links, list):
        for item in raw_links:
            if isinstance(item, dict) and item.get("url"):
                links.append(
                    ProjectLink(
                        label=str(item.get("label") or "Link"),
                        url=str(item["url"]),
                    )
                )
            elif isinstance(item, str) and item.startswith("http"):
                links.append(ProjectLink(label="Link", url=item))
            elif isinstance(item, str) and repo:
                links.append(ProjectLink(label=item or "Code", url=repo))

    if repo and not any(l.url == repo for l in links):
        links.insert(0, ProjectLink(label="Code", url=repo))

    live = str(row.get("live_url") or row.get("homepage") or "")
    if live:
        links.append(ProjectLink(label="Live", url=live))

    return links


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
      "url": "",
      "why_strong": "",
      "impact_hints": []
    }}
  ],
  "seniority_signal": "",
  "domains": []
}}
Pick at most 5 strongest non-toy projects. Always copy each project's url field from input when present."""
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

    prompt = f"""You write SKILLS sections for senior engineering resumes (ATS).
Target role: {state["target_role"]}
Languages seen: {sorted(langs)}
Topics seen: {sorted(topics)}
Analysis: {json.dumps(analysis)[:3000]}

Return ONLY JSON:
{{
  "headline_tech": ["React Native", "TypeScript", "Python"],
  "skills": [
    {{"category": "Languages", "items": []}},
    {{"category": "Mobile", "items": []}},
    {{"category": "AI & ML", "items": []}},
    {{"category": "Frontend", "items": []}},
    {{"category": "Backend", "items": []}},
    {{"category": "Databases", "items": []}},
    {{"category": "Tooling", "items": []}}
  ]
}}
Rules: only credible skills; 4-12 items/category; drop empty categories; headline_tech 5-8 items."""
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
    analysis = state["raw_data"].get("analysis", {})
    top = analysis.get("top_projects") or state["raw_data"].get("repos", [])[:5]
    user = state["user_info"]
    role = state["target_role"]

    prompt = f"""You are an elite tech resume writer. Voice: confident, concise, senior IC.
Target role: {role}
Candidate: {user.get("full_name", "")}

GitHub project evidence (include url on every project):
{json.dumps(top, indent=2)[:8000]}

Return ONLY JSON:
{{
  "summary": "2-3 sentences, no first-person pronouns, quantified where possible",
  "experience": [
    {{
      "company": "Independent / Open Source",
      "company_url": "",
      "title": "{role}",
      "location": "Remote",
      "start": "2023",
      "end": "Present",
      "bullets": ["Built ...", "Engineered ..."]
    }}
  ],
  "projects": [
    {{
      "name": "ProjectName",
      "stack": ["Python", "TypeScript"],
      "repo_url": "https://github.com/user/repo",
      "links": [
        {{"label": "Code", "url": "https://github.com/user/repo"}},
        {{"label": "Live", "url": "https://example.com"}}
      ],
      "bullets": ["Built ...", "Engineered ..."]
    }}
  ]
}}

HARD RULES:
- Start bullets with Built/Engineered/Architected/Delivered/Implemented/Optimized
- 2-4 experience entries; 3-5 projects
- Always set repo_url from evidence url when available
- Never invent FAANG employers
- summary: quote-ready professional blurb"""
    try:
        parsed = _parse_json(_invoke_text(prompt))
        if not isinstance(parsed, dict):
            raise ValueError("bad exp")
        state["experience_bullets"] = parsed.get("experience") or []
        state["draft"] = parsed
    except Exception:
        state["experience_bullets"] = []
        state["draft"] = {
            "summary": (
                f"{role} with hands-on experience shipping full-stack, mobile, "
                "and AI-integrated systems from real repositories."
            ),
            "experience": [],
            "projects": [
                {
                    "name": p.get("name", "Project"),
                    "stack": p.get("languages") or [],
                    "repo_url": p.get("url") or "",
                    "links": (
                        [{"label": "Code", "url": p.get("url")}]
                        if p.get("url")
                        else []
                    ),
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
    repo_map = _repo_url_map(state.get("raw_data") or {})

    summary = (draft.get("summary") or "").strip()
    if len(summary) < 40:
        summary = (
            f"{state['target_role']} with hands-on experience across full-stack, "
            "mobile, and AI-integrated systems, shipping production-quality work "
            "from real repositories and iterative delivery."
        )

    skill_cats: list[SkillCategory] = []
    for row in skills_payload.get("skills") or []:
        if isinstance(row, dict) and row.get("items"):
            skill_cats.append(
                SkillCategory(
                    category=str(row.get("category") or "Skills"),
                    items=[str(x) for x in row.get("items") or []],
                )
            )

    experience: list[ExperienceItem] = []
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
                company_url=str(row.get("company_url") or ""),
            )
        )

    projects: list[ProjectItem] = []
    for row in draft.get("projects") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "Project")
        repo_url = str(
            row.get("repo_url")
            or row.get("url")
            or repo_map.get(name.lower())
            or ""
        )
        projects.append(
            ProjectItem(
                name=name,
                stack=[
                    str(s)
                    for s in (row.get("stack") or row.get("languages") or [])
                ],
                repo_url=repo_url,
                links=_normalize_project_links(
                    {**row, "repo_url": repo_url, "name": name},
                    repo_map,
                ),
                bullets=[str(b) for b in (row.get("bullets") or []) if b],
            )
        )

    education = [
        EducationItem(
            school="Coding Temple",
            credential="Software Engineering Certificate",
            url="https://www.codingtemple.com/",
        ),
        EducationItem(
            school="Jackson Memorial High School",
            credential="High School Diploma",
            url="https://www.jacksonsd.org/",
        ),
    ]

    github = str(
        user.get("github")
        or (
            f"https://github.com/{user.get('username')}"
            if user.get("username")
            else ""
        )
    )

    doc = ResumeDocument(
        full_name=str(user.get("full_name") or "Software Engineer"),
        phone=str(user.get("phone") or ""),
        email=str(user.get("email") or ""),
        linkedin=str(user.get("linkedin") or ""),
        github=github,
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