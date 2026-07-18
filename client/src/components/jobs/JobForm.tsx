import { useMemo, useState } from "react";
import type {
    HiringTeamMember,
    JobSource,
    JobStage,
    LinkedInJobDetails,
    ParsedJobUrl,
} from "../../types/jobs";

type Props = {
    onCreate: (payload: Record<string, unknown>) => Promise<void>;
};

function createEmptyDetails(): LinkedInJobDetails {
    return {
        compensation: "N/A",
        location: "N/A",
        primary_responsibilities: "N/A",
        candidate_qualifications: "N/A",
        why_join: "N/A",
        about_company: "N/A",
        benefits: "N/A",
        requirements_added_by_poster: "N/A",
        hiring_team: [],
    };
}

function normalizeMember(
    p: Partial<HiringTeamMember> | null | undefined
): HiringTeamMember {
    return {
        name: p?.name || "N/A",
        title: p?.title || p?.headline || "N/A",
        headline: p?.headline || p?.title || "",
        company: p?.company || "",
        email: p?.email || "",
        phone: p?.phone || "",
        profile_url: p?.profile_url || "",
        connection_degree: p?.connection_degree || "",
        extra: p?.extra || "",
    };
}

function normalizeDetails(
    ld: Partial<LinkedInJobDetails> | null | undefined
): LinkedInJobDetails {
    const base = createEmptyDetails();
    if (!ld) return base;
    return {
        compensation: ld.compensation || "N/A",
        location: ld.location || "N/A",
        primary_responsibilities: ld.primary_responsibilities || "N/A",
        candidate_qualifications: ld.candidate_qualifications || "N/A",
        why_join: ld.why_join || "N/A",
        about_company: ld.about_company || "N/A",
        benefits: ld.benefits || "N/A",
        requirements_added_by_poster: ld.requirements_added_by_poster || "N/A",
        hiring_team: Array.isArray(ld.hiring_team)
            ? ld.hiring_team.map((m) => normalizeMember(m))
            : [],
    };
}

function formatWhen(iso: string): string {
    if (!iso) return "now";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
}

function Section({ title, body }: { title: string; body: string }) {
    const text = body && body.trim() ? body : "N/A";
    return (
        <div className="border border-slate-700/80 rounded-xl p-3 bg-slate-800/40">
            <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
                {title}
            </div>
            <div className="text-xs text-slate-200 whitespace-pre-wrap break-words leading-relaxed">
                {text}
            </div>
        </div>
    );
}

function hiringTeamOrNa(
    team: HiringTeamMember[] | undefined
): HiringTeamMember[] {
    if (team && team.length > 0) return team;
    return [normalizeMember({ name: "N/A", title: "N/A", headline: "N/A" })];
}

export default function JobForm({ onCreate }: Props) {
    const [url, setUrl] = useState("");
    const [fetching, setFetching] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const [warnings, setWarnings] = useState<string[]>([]);
    const [confidence, setConfidence] = useState<number | null>(null);

    const [company, setCompany] = useState("");
    const [roleTitle, setRoleTitle] = useState("");
    const [location, setLocation] = useState("");
    const [source, setSource] = useState<JobSource>("linkedin");
    const [stage, setStage] = useState<JobStage>("applied");
    const [jobUrl, setJobUrl] = useState("");
    const [salaryRange, setSalaryRange] = useState("");
    const [appliedDate, setAppliedDate] = useState("");
    const [appliedAt, setAppliedAt] = useState("");
    const [notes, setNotes] = useState("");
    const [tailored, setTailored] = useState(true);
    const [referral, setReferral] = useState(false);
    const [resumeTargetRole, setResumeTargetRole] = useState(
        "Senior Software Engineer"
    );
    const [rejectionReason, setRejectionReason] = useState("");
    const [details, setDetails] =
        useState<LinkedInJobDetails>(createEmptyDetails);
    const [unlocked, setUnlocked] = useState(false);

    const filled = useMemo(
        () => Boolean(company || roleTitle || jobUrl),
        [company, roleTitle, jobUrl]
    );

    const people = hiringTeamOrNa(details.hiring_team);

    const applyParsed = (data: ParsedJobUrl) => {
        const ld = normalizeDetails(data.linkedin_details);
        setJobUrl(data.job_url || url.trim());
        setCompany(data.company || "");
        setRoleTitle(data.role_title || "");
        setLocation(data.location || "Remote");
        setSource("linkedin");
        setSalaryRange(data.salary_range || "");
        setNotes(data.notes || "");
        setAppliedDate(data.applied_date || new Date().toISOString().slice(0, 10));
        setAppliedAt(data.applied_at || new Date().toISOString());
        setConfidence(
            typeof data.confidence === "number" ? data.confidence : null
        );
        setWarnings(Array.isArray(data.warnings) ? data.warnings : []);
        setDetails(ld);
        if (data.role_title) {
            setResumeTargetRole(data.role_title);
        }
        setStage("applied");
        setUnlocked(false);
    };

    const fetchFromUrl = async () => {
        const trimmed = url.trim();
        if (!trimmed) {
            setError("Paste a LinkedIn job URL first");
            return;
        }
        if (!/linkedin\.com/i.test(trimmed)) {
            setError("Only LinkedIn job URLs are supported right now");
            return;
        }
        setFetching(true);
        setError("");
        setWarnings([]);
        try {
            const res = await fetch("/api/jobs/parse-url", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: trimmed }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(
                    typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
                );
            }
            applyParsed(data as ParsedJobUrl);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to parse LinkedIn URL");
        } finally {
            setFetching(false);
        }
    };

    const reset = () => {
        setUrl("");
        setCompany("");
        setRoleTitle("");
        setLocation("");
        setSource("linkedin");
        setStage("applied");
        setJobUrl("");
        setSalaryRange("");
        setAppliedDate("");
        setAppliedAt("");
        setNotes("");
        setRejectionReason("");
        setDetails(createEmptyDetails());
        setConfidence(null);
        setWarnings([]);
        setUnlocked(false);
        setError("");
    };

    const submit = async () => {
        if (!jobUrl && !url.trim()) {
            setError("LinkedIn job URL is required");
            return;
        }
        if (!company.trim() || !roleTitle.trim()) {
            setError("Company and role are required — fetch from URL or edit fields");
            return;
        }
        setBusy(true);
        setError("");
        try {
            const nowIso = new Date().toISOString();
            await onCreate({
                company: company.trim(),
                role_title: roleTitle.trim(),
                location: location.trim() || details.location || "Remote",
                source,
                stage,
                job_url: (jobUrl || url).trim(),
                salary_range: salaryRange.trim() || details.compensation || "",
                applied_date: appliedDate || nowIso.slice(0, 10),
                applied_at: appliedAt || nowIso,
                resume_target_role: resumeTargetRole.trim(),
                tailored,
                referral,
                notes: notes.trim(),
                rejection_reason: rejectionReason.trim(),
                linkedin_details: details,
            });
            reset();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to save");
        } finally {
            setBusy(false);
        }
    };

    const box =
        "w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500";

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-3">
            <div>
                <h3 className="font-semibold">Log LinkedIn application</h3>
                <p className="text-xs text-slate-400 mt-1">
                    Paste a LinkedIn job URL. We extract About the job sections and Meet
                    the hiring team automatically, and stamp applied date/time.
                </p>
            </div>

            {error ? (
                <div className="text-xs text-red-300 border border-red-900 bg-red-950/40 rounded-lg px-3 py-2">
                    {error}
                </div>
            ) : null}

            {warnings.length > 0 ? (
                <div className="text-xs text-amber-200/90 border border-amber-900/50 bg-amber-950/30 rounded-lg px-3 py-2 space-y-1">
                    {warnings.map((w, i) => (
                        <div key={i}>{w}</div>
                    ))}
                </div>
            ) : null}

            <div className="space-y-2">
                <label className="text-xs text-slate-400" htmlFor="job-url-input">
                    LinkedIn job URL
                </label>
                <input
                    id="job-url-input"
                    className={box}
                    placeholder="https://www.linkedin.com/jobs/view/1234567890"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            void fetchFromUrl();
                        }
                    }}
                />
                <button
                    type="button"
                    disabled={fetching || !url.trim()}
                    onClick={() => void fetchFromUrl()}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 py-2.5 rounded-xl text-sm font-semibold"
                >
                    {fetching ? "Reading LinkedIn post..." : "Fetch details from LinkedIn"}
                </button>
            </div>

            {filled ? (
                <>
                    <div className="flex items-center justify-between pt-1">
                        <div className="text-xs text-slate-400">
                            Applied{" "}
                            <span className="text-slate-200">{formatWhen(appliedAt)}</span>
                            {confidence != null ? (
                                <span className="ml-2 text-slate-500">
                                    · confidence {Math.round(confidence * 100)}%
                                </span>
                            ) : null}
                        </div>
                        <button
                            type="button"
                            className="text-xs text-blue-400 hover:text-blue-300"
                            onClick={() => setUnlocked((u) => !u)}
                        >
                            {unlocked ? "Lock fields" : "Edit fields"}
                        </button>
                    </div>

                    <input
                        className={box}
                        readOnly={!unlocked}
                        placeholder="Company"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                    />
                    <input
                        className={box}
                        readOnly={!unlocked}
                        placeholder="Role title"
                        value={roleTitle}
                        onChange={(e) => setRoleTitle(e.target.value)}
                    />
                    <input
                        className={box}
                        readOnly={!unlocked}
                        placeholder="Location"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    />
                    <input
                        className={box}
                        readOnly={!unlocked}
                        placeholder="Compensation"
                        value={salaryRange}
                        onChange={(e) => setSalaryRange(e.target.value)}
                    />

                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                            About the job
                        </div>
                        <Section title="Compensation" body={details.compensation} />
                        <Section title="Location" body={details.location} />
                        <Section
                            title="Primary Responsibilities"
                            body={details.primary_responsibilities}
                        />
                        <Section
                            title="Candidate Qualifications"
                            body={details.candidate_qualifications}
                        />
                        <Section title="Why Join This Opportunity" body={details.why_join} />
                        <Section title="About Company" body={details.about_company} />
                        <Section title="Benefits found in job post" body={details.benefits} />
                        <Section
                            title="Requirements added by the job poster"
                            body={details.requirements_added_by_poster}
                        />

                        <div className="border border-slate-700/80 rounded-xl p-3 bg-slate-800/40">
                            <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-2">
                                Meet the hiring team
                            </div>
                            <div className="space-y-2">
                                {people.map((p, i) => {
                                    const headline =
                                        (p.headline && p.headline.trim()) ||
                                        (p.title && p.title.trim()) ||
                                        "N/A";
                                    return (
                                        <div
                                            key={`${p.name}-${i}`}
                                            className="text-xs text-slate-200 border border-slate-700 rounded-lg px-2.5 py-2"
                                        >
                                            <div className="font-medium text-slate-100">
                                                {p.name || "N/A"}
                                            </div>
                                            {p.connection_degree ? (
                                                <div className="text-slate-500 mt-0.5">
                                                    {p.connection_degree}
                                                </div>
                                            ) : null}
                                            <div className="text-slate-300 mt-1 whitespace-pre-wrap break-words leading-relaxed">
                                                {headline}
                                            </div>
                                            {p.email ? (
                                                <a
                                                    href={`mailto:${p.email}`}
                                                    className="text-blue-400 hover:underline mt-1 block break-all"
                                                >
                                                    {p.email}
                                                </a>
                                            ) : null}
                                            {p.phone ? (
                                                <a
                                                    href={`tel:${p.phone.replace(/[^\d+]/g, "")}`}
                                                    className="text-blue-400 hover:underline block"
                                                >
                                                    {p.phone}
                                                </a>
                                            ) : null}
                                            {p.profile_url ? (
                                                <a
                                                    href={p.profile_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="text-blue-400 hover:underline mt-1 inline-block"
                                                >
                                                    Profile
                                                </a>
                                            ) : null}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    <input
                        className={box}
                        placeholder="Resume target role"
                        value={resumeTargetRole}
                        onChange={(e) => setResumeTargetRole(e.target.value)}
                    />

                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                            type="checkbox"
                            checked={tailored}
                            onChange={(e) => setTailored(e.target.checked)}
                        />
                        Tailored resume/application
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                            type="checkbox"
                            checked={referral}
                            onChange={(e) => setReferral(e.target.checked)}
                        />
                        Referral / warm intro
                    </label>

                    <textarea
                        className={box}
                        rows={2}
                        placeholder="Rejection reason (only if rejected)"
                        value={rejectionReason}
                        onChange={(e) => setRejectionReason(e.target.value)}
                    />

                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => void submit()}
                        className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 py-2.5 rounded-xl text-sm font-semibold"
                    >
                        {busy ? "Saving..." : "Add application"}
                    </button>
                </>
            ) : null}
        </div>
    );
}