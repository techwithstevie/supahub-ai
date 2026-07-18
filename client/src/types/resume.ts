export type SkillCategory = {
    category: string;
    items: string[];
};

export type ExperienceItem = {
    company: string;
    title: string;
    location: string;
    start: string;
    end: string;
    bullets: string[];
    company_url: string;
};

export type ProjectLink = {
    label: string;
    url: string;
};

export type ProjectItem = {
    name: string;
    stack: string[];
    links: ProjectLink[];
    bullets: string[];
    repo_url: string;
};

export type EducationItem = {
    school: string;
    credential: string;
    url: string;
    year: string;
};

export type ResumeDocument = {
    full_name: string;
    phone: string;
    email: string;
    linkedin: string;
    github: string;
    portfolio: string;
    target_title: string;
    headline_tech: string[];
    summary: string;
    skills: SkillCategory[];
    experience: ExperienceItem[];
    projects: ProjectItem[];
    education: EducationItem[];
};

export type ResumeSection =
    | "header"
    | "summary"
    | "skills"
    | "experience"
    | "projects"
    | "education";

export const emptyResume = (): ResumeDocument => ({
    full_name: "",
    phone: "",
    email: "",
    linkedin: "",
    github: "",
    portfolio: "",
    target_title: "Senior Software Engineer",
    headline_tech: [],
    summary: "",
    skills: [],
    experience: [],
    projects: [],
    education: [],
});