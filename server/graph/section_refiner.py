from __future__ import annotations

import json
from typing import Any

from langchain_ollama import ChatOllama

from config import settings
from models.schemas import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ProjectLink,
    ResumeDocument,
    ResumeSection,
    SkillCategory,
)

llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.3,
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
            ln
            for ln in cleaned.split("\n")
            if not ln.strip().startswith("```")
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


_SECTION_SCHEMAS: dict[ResumeSection, str] = {
    ResumeSection.header: """{
  "full_name": "",
  "phone": "",
  "email": "",
  "linkedin": "",
  "github": "",
  "portfolio": "",
  "target_title": "",
  "headline_tech": ["Tech1", "Tech2"]
}""",
    ResumeSection.summary: """{
  "summary": "professional blurb, no first-person pronouns"
}""",
    ResumeSection.skills: """{
  "skills": [
    {"category": "Languages", "items": ["TypeScript", "Python"]}
  ],
  "headline_tech": ["optional", "update", "if needed"]
}""",
    ResumeSection.experience: """{
  "experience": [
    {
      "company": "",
      "company_url": "",
      "title": "",
      "location": "Remote",
      "start": "",
      "end": "Present",
      "bullets": ["Built ...", "Engineered ..."]
    }
  ]
}""",
    ResumeSection.projects: """{
  "projects": [
    {
      "name": "",
      "stack": [],
      "repo_url": "",
      "links": [{"label": "Code", "url": "https://..."}],
      "bullets": ["Built ..."]
    }
  ]
}""",
    ResumeSection.education: """{
  "education": [
    {"school": "", "credential": "", "url": "", "year": ""}
  ]
}""",
}


def _current_slice(doc: ResumeDocument, section: ResumeSection) -> dict[str, Any]:
    data = doc.model_dump()
    if section == ResumeSection.header:
        return {
            "full_name": data["full_name"],
            "phone": data["phone"],
            "email": data["email"],
            "linkedin": data["linkedin"],
            "github": data["github"],
            "portfolio": data["portfolio"],
            "target_title": data["target_title"],
            "headline_tech": data["headline_tech"],
        }
    if section == ResumeSection.summary:
        return {"summary": data["summary"]}
    if section == ResumeSection.skills:
        return {
            "skills": data["skills"],
            "headline_tech": data["headline_tech"],
        }
    if section == ResumeSection.experience:
        return {"experience": data["experience"]}
    if section == ResumeSection.projects:
        return {"projects": data["projects"]}
    if section == ResumeSection.education:
        return {"education": data["education"]}
    return {}


def _merge_header(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    updates: dict[str, Any] = {}
    for key in (
        "full_name",
        "phone",
        "email",
        "linkedin",
        "github",
        "portfolio",
        "target_title",
    ):
        if key in patch and patch[key] is not None:
            updates[key] = str(patch[key])
    if "headline_tech" in patch and isinstance(patch["headline_tech"], list):
        updates["headline_tech"] = [str(x) for x in patch["headline_tech"]]
    return doc.model_copy(update=updates)


def _merge_summary(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    summary = patch.get("summary")
    if summary is None:
        return doc
    return doc.model_copy(update={"summary": str(summary).strip()})


def _merge_skills(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    updates: dict[str, Any] = {}
    if isinstance(patch.get("skills"), list):
        cats: list[SkillCategory] = []
        for row in patch["skills"]:
            if isinstance(row, dict) and row.get("items") is not None:
                cats.append(
                    SkillCategory(
                        category=str(row.get("category") or "Skills"),
                        items=[str(x) for x in (row.get("items") or [])],
                    )
                )
        updates["skills"] = cats
    if isinstance(patch.get("headline_tech"), list):
        updates["headline_tech"] = [str(x) for x in patch["headline_tech"]]
    return doc.model_copy(update=updates) if updates else doc


def _merge_experience(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    rows = patch.get("experience")
    if not isinstance(rows, list):
        return doc
    experience: list[ExperienceItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        experience.append(
            ExperienceItem(
                company=str(row.get("company") or ""),
                title=str(row.get("title") or ""),
                location=str(row.get("location") or "Remote"),
                start=str(row.get("start") or ""),
                end=str(row.get("end") or "Present"),
                bullets=[str(b) for b in (row.get("bullets") or []) if b],
                company_url=str(row.get("company_url") or ""),
            )
        )
    return doc.model_copy(update={"experience": experience})


def _merge_projects(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    rows = patch.get("projects")
    if not isinstance(rows, list):
        return doc
    projects: list[ProjectItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        links: list[ProjectLink] = []
        for ln in row.get("links") or []:
            if isinstance(ln, dict) and ln.get("url"):
                links.append(
                    ProjectLink(
                        label=str(ln.get("label") or "Link"),
                        url=str(ln["url"]),
                    )
                )
        projects.append(
            ProjectItem(
                name=str(row.get("name") or "Project"),
                stack=[str(s) for s in (row.get("stack") or [])],
                repo_url=str(row.get("repo_url") or row.get("url") or ""),
                links=links,
                bullets=[str(b) for b in (row.get("bullets") or []) if b],
            )
        )
    return doc.model_copy(update={"projects": projects})


def _merge_education(doc: ResumeDocument, patch: dict[str, Any]) -> ResumeDocument:
    rows = patch.get("education")
    if not isinstance(rows, list):
        return doc
    education: list[EducationItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        education.append(
            EducationItem(
                school=str(row.get("school") or ""),
                credential=str(row.get("credential") or ""),
                url=str(row.get("url") or ""),
                year=str(row.get("year") or ""),
            )
        )
    return doc.model_copy(update={"education": education})


_MERGERS = {
    ResumeSection.header: _merge_header,
    ResumeSection.summary: _merge_summary,
    ResumeSection.skills: _merge_skills,
    ResumeSection.experience: _merge_experience,
    ResumeSection.projects: _merge_projects,
    ResumeSection.education: _merge_education,
}


def refine_section(
    doc: ResumeDocument,
    section: ResumeSection,
    user_prompt: str,
) -> ResumeDocument:
    current = _current_slice(doc, section)
    schema = _SECTION_SCHEMAS[section]

    prompt = f"""You are an elite resume editor for senior software engineers.
Edit ONLY the "{section.value}" section based on the user's instruction.
Keep a professional ATS tone. Do not invent fake FAANG employers.
Preserve working URLs when present. Strengthen bullets with action verbs.

CURRENT SECTION JSON:
{json.dumps(current, indent=2)}

USER INSTRUCTION:
{user_prompt.strip()}

Return ONLY valid JSON matching this shape (no markdown, no commentary):
{schema}
"""
    try:
        patch = _parse_json(_invoke_text(prompt))
        if not isinstance(patch, dict):
            raise ValueError("refiner returned non-object")
    except Exception:
        return doc

    merger = _MERGERS[section]
    return merger(doc, patch)