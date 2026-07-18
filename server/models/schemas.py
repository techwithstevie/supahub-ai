from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResumeRequest(BaseModel):
    github_username: str
    github_token: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    target_role: Optional[str] = "Senior Software Engineer"
    location: Optional[str] = None


class SkillCategory(BaseModel):
    category: str
    items: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    company: str
    title: str
    location: str = "Remote"
    start: str = ""
    end: str = "Present"
    bullets: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str
    stack: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    school: str
    credential: str


class ResumeDocument(BaseModel):
    """Matches professional single-column ATS resume (Stephen sample)."""

    full_name: str = ""
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    target_title: str = "Senior Software Engineer"
    headline_tech: list[str] = Field(default_factory=list)
    summary: str = ""
    skills: list[SkillCategory] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)


class ResumeResponse(BaseModel):
    resume: ResumeDocument
    resume_html: str
    resume_markdown: str
    agent_log: list[str] = Field(default_factory=list)
    raw_skills: dict[str, Any] = Field(default_factory=dict)