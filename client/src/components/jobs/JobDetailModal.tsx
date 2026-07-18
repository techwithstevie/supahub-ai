import type { JobApplication, LinkedInJobDetails } from "../../types/jobs";

type Props = {
  app: JobApplication | null;
  onClose: () => void;
};

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "N/A";
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

function Section({ title, body }: { title: string; body?: string | null }) {
  const text = body && body.trim() ? body : "N/A";
  return (
    <div className="border border-slate-700/80 rounded-xl p-3 bg-slate-800/50">
      <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
        {title}
      </div>
      <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
        {text}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-sm text-slate-100 mt-0.5 break-words">
        {value && value.trim() ? value : "N/A"}
      </div>
    </div>
  );
}

function LinkedInBlock({ details }: { details: LinkedInJobDetails }) {
  const team =
    details.hiring_team && details.hiring_team.length > 0
      ? details.hiring_team
      : [
          {
            name: "N/A",
            title: "N/A",
            profile_url: "",
            connection_degree: "",
            extra: "",
          },
        ];

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">
        About the job
      </h4>
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

      <div className="border border-slate-700/80 rounded-xl p-3 bg-slate-800/50">
        <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-2">
          Meet the hiring team
        </div>
        <div className="space-y-2">
          {team.map((p, i) => (
            <div
              key={`${p.name}-${i}`}
              className="border border-slate-700 rounded-lg px-3 py-2 text-sm"
            >
              <div className="font-medium text-slate-100">{p.name || "N/A"}</div>
              <div className="text-slate-400 text-xs mt-0.5">
                {p.title || "N/A"}
              </div>
              {p.connection_degree ? (
                <div className="text-xs text-slate-500 mt-0.5">
                  {p.connection_degree}
                </div>
              ) : null}
              {p.extra ? (
                <div className="text-xs text-slate-500 mt-0.5">{p.extra}</div>
              ) : null}
              {p.profile_url ? (
                <a
                  href={p.profile_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-blue-400 hover:underline mt-1 inline-block"
                  onClick={(e) => e.stopPropagation()}
                >
                  LinkedIn profile
                </a>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function JobDetailModal({ app, onClose }: Props) {
  if (!app) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="job-detail-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        aria-label="Close modal"
        onClick={onClose}
      />

      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl flex flex-col">
        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-800 shrink-0">
          <div className="min-w-0">
            <h3
              id="job-detail-title"
              className="text-lg font-semibold text-white truncate"
            >
              {app.role_title || "Application"}
            </h3>
            <p className="text-sm text-slate-400 truncate">{app.company}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 text-sm"
          >
            Close
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-4 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Company" value={app.company} />
            <Field label="Role" value={app.role_title} />
            <Field label="Location" value={app.location} />
            <Field label="Source" value={app.source} />
            <Field label="Stage" value={app.stage} />
            <Field label="Compensation" value={app.salary_range} />
            <Field label="Applied" value={formatWhen(app.applied_at || app.applied_date)} />
            <Field label="Target role" value={app.resume_target_role} />
            <Field
              label="Flags"
              value={[
                app.tailored ? "tailored" : "cold",
                app.referral ? "referral" : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            />
            <Field label="Created" value={formatWhen(app.created_at)} />
          </div>

          {app.job_url ? (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                Job URL
              </div>
              <a
                href={app.job_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-blue-400 hover:underline break-all"
              >
                {app.job_url}
              </a>
            </div>
          ) : null}

          {app.notes ? <Section title="Notes" body={app.notes} /> : null}

          {app.rejection_reason ? (
            <Section title="Rejection reason" body={app.rejection_reason} />
          ) : null}

          {app.linkedin_details ? (
            <LinkedInBlock details={app.linkedin_details} />
          ) : (
            <div className="text-xs text-slate-500 border border-slate-800 rounded-xl p-3">
              No structured LinkedIn About the job data stored for this
              application.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}