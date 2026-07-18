from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStage(str, Enum):
    saved = "saved"
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    accepted = "accepted"
    rejected = "rejected"
    ghosted = "ghosted"
    withdrawn = "withdrawn"


class JobSource(str, Enum):
    linkedin = "linkedin"
    other = "other"


class HiringTeamMember(BaseModel):
    name: str = "N/A"
    title: str = "N/A"
    profile_url: str = ""
    connection_degree: str = ""  # e.g. "1st", "2nd"
    extra: str = ""  # any other shown detail


class LinkedInJobDetails(BaseModel):
    """Structured sections from a LinkedIn job post."""

    compensation: str = "N/A"
    location: str = "N/A"
    primary_responsibilities: str = "N/A"
    candidate_qualifications: str = "N/A"
    why_join: str = "N/A"  # Why Join This Opportunity
    about_company: str = "N/A"  # About <company>
    benefits: str = "N/A"  # Benefits found in job post
    requirements_added_by_poster: str = "N/A"  # Requirements added by the job poster
    hiring_team: list[HiringTeamMember] = Field(default_factory=list)

    def hiring_team_or_na(self) -> list[HiringTeamMember]:
        if self.hiring_team:
            return self.hiring_team
        return [HiringTeamMember(name="N/A", title="N/A")]


class JobApplicationCreate(BaseModel):
    company: str = ""
    role_title: str = ""
    location: str = "Remote"
    source: JobSource = JobSource.linkedin
    stage: JobStage = JobStage.applied
    job_url: str = ""
    salary_range: str = ""
    applied_date: Optional[date] = None
    applied_at: Optional[datetime] = None
    resume_target_role: str = ""
    tailored: bool = False
    referral: bool = False
    notes: str = ""
    rejection_reason: str = ""
    linkedin_details: Optional[LinkedInJobDetails] = None


class JobApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role_title: Optional[str] = None
    location: Optional[str] = None
    source: Optional[JobSource] = None
    stage: Optional[JobStage] = None
    job_url: Optional[str] = None
    salary_range: Optional[str] = None
    applied_date: Optional[date] = None
    applied_at: Optional[datetime] = None
    resume_target_role: Optional[str] = None
    tailored: Optional[bool] = None
    referral: Optional[bool] = None
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    linkedin_details: Optional[LinkedInJobDetails] = None


class JobApplication(JobApplicationCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FunnelMetrics(BaseModel):
    total: int = 0
    by_stage: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    applied_count: int = 0
    response_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    rejected_count: int = 0
    ghosted_count: int = 0
    tailored_count: int = 0
    referral_count: int = 0
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    ghost_rate: float = 0.0
    tailored_interview_rate: float = 0.0
    untailored_interview_rate: float = 0.0
    referral_interview_rate: float = 0.0
    cold_interview_rate: float = 0.0
    avg_days_in_pipeline: float = 0.0
    top_rejection_themes: list[str] = Field(default_factory=list)


class JobMetricsResponse(BaseModel):
    metrics: FunnelMetrics
    applications: list[JobApplication]
    insights_ready: bool = True


class AnalyzeJobSearchRequest(BaseModel):
    focus: str = ""
    include_notes: bool = True


class AnalyzeJobSearchResponse(BaseModel):
    metrics: FunnelMetrics
    diagnosis: str
    root_causes: list[str]
    strengths: list[str]
    action_plan: list[str]
    resume_recommendations: list[str]
    outreach_recommendations: list[str]
    priority_score: dict[str, int] = Field(default_factory=dict)
    raw_agent_json: dict[str, Any] = Field(default_factory=dict)
    agent_log: list[str] = Field(default_factory=list)


class ParseJobUrlRequest(BaseModel):
    url: str


class ParseJobUrlResponse(BaseModel):
    job_url: str
    company: str = ""
    role_title: str = ""
    location: str = ""
    source: JobSource = JobSource.linkedin
    salary_range: str = ""
    notes: str = ""
    applied_date: date
    applied_at: datetime
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    linkedin_details: LinkedInJobDetails = Field(default_factory=LinkedInJobDetails)
    raw: dict[str, Any] = Field(default_factory=dict)