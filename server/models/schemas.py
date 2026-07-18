from pydantic import BaseModel, Field
from typing import Any, Optional


class ResumeRequest(BaseModel):
    github_username: str
    github_token: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    target_role: Optional[str] = "Software Engineer"


class ResumeResponse(BaseModel):
    resume_markdown: str
    skills: dict[str, Any] = Field(default_factory=dict)
    projects: list[Any] = Field(default_factory=list)
    agent_log: list[str] = Field(default_factory=list)