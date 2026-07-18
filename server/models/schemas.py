from pydantic import BaseModel
from typing import List, Optional

class ResumeRequest(BaseModel):
    github_username: str
    github_token: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    target_role: Optional[str] = "Software Engineer"

class AgentState(BaseModel):
    username: str
    raw_data: dict = {}
    skills: List[str] = []
    experience_bullets: List[dict] = []
    resume_markdown: str = ""
    status: str = "idle"