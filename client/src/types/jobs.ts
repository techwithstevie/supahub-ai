export type JobStage =
    | "saved"
    | "applied"
    | "screening"
    | "interview"
    | "offer"
    | "accepted"
    | "rejected"
    | "ghosted"
    | "withdrawn";

export type JobSource = "linkedin" | "other";

export type HiringTeamMember = {
    name: string;
    title: string; // full subtitle under the name (company | role | email | phone)
    headline: string;
    company: string;
    email: string;
    phone: string;
    profile_url: string;
    connection_degree: string;
    extra: string;
};

export type LinkedInJobDetails = {
    compensation: string;
    location: string;
    primary_responsibilities: string;
    candidate_qualifications: string;
    why_join: string;
    about_company: string;
    benefits: string;
    requirements_added_by_poster: string;
    hiring_team: HiringTeamMember[];
};

export type JobApplication = {
    id: string;
    company: string;
    role_title: string;
    location: string;
    source: JobSource;
    stage: JobStage;
    job_url: string;
    salary_range: string;
    applied_date: string | null;
    applied_at?: string | null;
    resume_target_role: string;
    tailored: boolean;
    referral: boolean;
    notes: string;
    rejection_reason: string;
    linkedin_details?: LinkedInJobDetails | null;
    created_at: string;
    updated_at: string;
};

export type FunnelMetrics = {
    total: number;
    by_stage: Record<string, number>;
    by_source: Record<string, number>;
    applied_count: number;
    response_count: number;
    interview_count: number;
    offer_count: number;
    rejected_count: number;
    ghosted_count: number;
    tailored_count: number;
    referral_count: number;
    response_rate: number;
    interview_rate: number;
    offer_rate: number;
    ghost_rate: number;
    tailored_interview_rate: number;
    untailored_interview_rate: number;
    referral_interview_rate: number;
    cold_interview_rate: number;
    avg_days_in_pipeline: number;
    top_rejection_themes: string[];
};

export type JobAnalysis = {
    metrics: FunnelMetrics;
    diagnosis: string;
    root_causes: string[];
    strengths: string[];
    action_plan: string[];
    resume_recommendations: string[];
    outreach_recommendations: string[];
    priority_score: Record<string, number>;
    agent_log: string[];
};

export type ParsedJobUrl = {
    job_url: string;
    company: string;
    role_title: string;
    location: string;
    source: JobSource;
    salary_range: string;
    notes: string;
    applied_date: string;
    applied_at: string;
    confidence: number;
    warnings: string[];
    linkedin_details: LinkedInJobDetails;
};

export const STAGES: JobStage[] = [
    "saved",
    "applied",
    "screening",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "ghosted",
    "withdrawn",
];

export const SOURCES: JobSource[] = ["linkedin", "other"];

export const emptyLinkedInDetails = (): LinkedInJobDetails => ({
    compensation: "N/A",
    location: "N/A",
    primary_responsibilities: "N/A",
    candidate_qualifications: "N/A",
    why_join: "N/A",
    about_company: "N/A",
    benefits: "N/A",
    requirements_added_by_poster: "N/A",
    hiring_team: [],
});