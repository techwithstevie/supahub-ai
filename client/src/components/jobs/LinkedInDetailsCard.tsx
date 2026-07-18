import type { HiringTeamMember, LinkedInJobDetails } from "../../types/jobs";

type Props = {
    details: LinkedInJobDetails;
};

function Section({ title, body }: { title: string; body: string }) {
    const text = body?.trim() ? body : "N/A";
    return (
        <div className="border border-slate-700/80 rounded-xl p-3 bg-slate-800/40">
            <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
                {title}
            </div>
            <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto">
                {text}
            </div>
        </div>
    );
}

function teamList(team: HiringTeamMember[] | undefined): HiringTeamMember[] {
    if (team && team.length > 0) return team;
    return [
        {
            name: "N/A",
            title: "N/A",
            profile_url: "",
            connection_degree: "",
            extra: "",
        },
    ];
}

export default function LinkedInDetailsCard({ details }: Props) {
    const people = teamList(details.hiring_team);

    return (
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
                    {people.map((p, i) => (
                        <div
                            key={`${p.name}-${i}`}
                            className="text-xs text-slate-200 border border-slate-700 rounded-lg px-2.5 py-2"
                        >
                            <div className="font-medium text-slate-100">{p.name || "N/A"}</div>
                            <div className="text-slate-400">{p.title || "N/A"}</div>
                            {p.connection_degree ? (
                                <div className="text-slate-500">{p.connection_degree}</div>
                            ) : null}
                            {p.extra ? <div className="text-slate-500">{p.extra}</div> : null}
                            {p.profile_url ? (
                                <a
                                    href={p.profile_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-400 hover:underline"
                                >
                                    Profile
                                </a>
                            ) : null}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}