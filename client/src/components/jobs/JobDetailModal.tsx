import type {
  HiringTeamMember,
  JobApplication,
  LinkedInJobDetails,
} from "../../types/jobs";

type Props = {
  app: JobApplication | null;
  onClose: () => void;
};

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
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

function formatDateOnly(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function display(value?: string | null, fallback = "—"): string {
  if (value == null) return fallback;
  const t = String(value).trim();
  if (!t || t.toUpperCase() === "N/A") return fallback;
  return t;
}

function stageStyles(stage: string): string {
  const s = (stage || "").toLowerCase();
  if (s === "offer" || s === "accepted")
    return "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30";
  if (s === "rejected" || s === "withdrawn")
    return "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30";
  if (s === "interview" || s === "phone_screen" || s === "onsite")
    return "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30";
  if (s === "applied")
    return "bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-500/30";
  return "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/30";
}

function stageLabel(stage: string): string {
  if (!stage) return "Unknown";
  return stage
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function MetaItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-slate-100 break-words">{children}</dd>
    </div>
  );
}

function ContentBlock({
  title,
  body,
}: {
  title: string;
  body?: string | null;
}) {
  const text = display(body);
  return (
    <section className="rounded-lg border border-slate-700/70 bg-slate-950/40">
      <header className="border-b border-slate-700/60 px-4 py-2.5">
        <h4 className="text-[11px] font-semibold uppercase tracking-[0.07em] text-slate-400">
          {title}
        </h4>
      </header>
      <div className="px-4 py-3 text-[13px] leading-relaxed text-slate-200 whitespace-pre-wrap break-words">
        {text}
      </div>
    </section>
  );
}

function hiringTeamOrNa(
  team: HiringTeamMember[] | undefined | null
): HiringTeamMember[] {
  if (team && team.length > 0) return team;
  return [
    {
      name: "—",
      title: "—",
      headline: "—",
      company: "",
      email: "",
      phone: "",
      profile_url: "",
      connection_degree: "",
      extra: "",
    },
  ];
}

function ContactCard({ person }: { person: HiringTeamMember }) {
  const headline =
    display(person.headline, "") || display(person.title, "—");
  const hasContact = Boolean(person.email || person.phone || person.profile_url);

  return (
    <article className="rounded-lg border border-slate-700/70 bg-gradient-to-b from-slate-800/50 to-slate-900/40 px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h5 className="text-sm font-semibold text-white tracking-tight">
              {display(person.name)}
            </h5>
            {person.connection_degree ? (
              <span className="inline-flex items-center rounded-full bg-slate-700/80 px-2 py-0.5 text-[10px] font-medium text-slate-300 ring-1 ring-slate-600/80">
                {person.connection_degree}
              </span>
            ) : null}
            {person.extra ? (
              <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-200/90 ring-1 ring-amber-500/25">
                {person.extra}
              </span>
            ) : null}
          </div>
          <p className="mt-1.5 text-[12px] leading-relaxed text-slate-300 whitespace-pre-wrap break-words">
            {headline}
          </p>
        </div>
        <div
          className="shrink-0 h-9 w-9 rounded-full bg-slate-700/80 ring-1 ring-slate-600 flex items-center justify-center text-[11px] font-semibold text-slate-200"
          aria-hidden
        >
          {initials(person.name)}
        </div>
      </div>

      {hasContact ? (
        <div className="mt-3 pt-3 border-t border-slate-700/60 flex flex-col gap-1.5">
          {person.email ? (
            <a
              href={`mailto:${person.email}`}
              className="inline-flex items-center gap-2 text-[12px] text-sky-400 hover:text-sky-300 break-all"
              onClick={(e) => e.stopPropagation()}
            >
              <span className="text-slate-500 font-medium shrink-0 w-12">
                Email
              </span>
              <span className="underline-offset-2 hover:underline">
                {person.email}
              </span>
            </a>
          ) : null}
          {person.phone ? (
            <a
              href={`tel:${person.phone.replace(/[^\d+]/g, "")}`}
              className="inline-flex items-center gap-2 text-[12px] text-sky-400 hover:text-sky-300"
              onClick={(e) => e.stopPropagation()}
            >
              <span className="text-slate-500 font-medium shrink-0 w-12">
                Phone
              </span>
              <span className="underline-offset-2 hover:underline">
                {person.phone}
              </span>
            </a>
          ) : null}
          {person.profile_url ? (
            <a
              href={person.profile_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-[12px] text-sky-400 hover:text-sky-300"
              onClick={(e) => e.stopPropagation()}
            >
              <span className="text-slate-500 font-medium shrink-0 w-12">
                Profile
              </span>
              <span className="underline-offset-2 hover:underline truncate">
                View on LinkedIn
              </span>
            </a>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

function initials(name?: string | null): string {
  const parts = (name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0 || parts[0] === "—" || parts[0] === "N/A") return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function LinkedInBlock({ details }: { details: LinkedInJobDetails }) {
  const team = hiringTeamOrNa(details.hiring_team);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-700/80" />
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
          Position details
        </h3>
        <div className="h-px flex-1 bg-slate-700/80" />
      </div>

      <div className="grid gap-3">
        <ContentBlock title="Compensation" body={details.compensation} />
        <ContentBlock title="Location" body={details.location} />
        <ContentBlock
          title="Primary Responsibilities"
          body={details.primary_responsibilities}
        />
        <ContentBlock
          title="Candidate Qualifications"
          body={details.candidate_qualifications}
        />
        <ContentBlock
          title="Why Join This Opportunity"
          body={details.why_join}
        />
        <ContentBlock title="About Company" body={details.about_company} />
        <ContentBlock
          title="Benefits found in job post"
          body={details.benefits}
        />
        <ContentBlock
          title="Requirements added by the job poster"
          body={details.requirements_added_by_poster}
        />
      </div>

      <div className="rounded-lg border border-slate-700/70 bg-slate-950/40">
        <header className="border-b border-slate-700/60 px-4 py-2.5 flex items-center justify-between gap-2">
          <h4 className="text-[11px] font-semibold uppercase tracking-[0.07em] text-slate-400">
            Hiring team
          </h4>
          <span className="text-[10px] text-slate-500 font-medium">
            {team.length === 1 && display(team[0].name) === "—"
              ? "No contacts"
              : `${team.length} contact${team.length === 1 ? "" : "s"}`}
          </span>
        </header>
        <div className="p-3 space-y-2.5">
          {team.map((p, i) => (
            <ContactCard key={`${p.name}-${i}`} person={p} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function JobDetailModal({ app, onClose }: Props) {
  if (!app) return null;

  const flagChips = [
    app.tailored ? "Tailored application" : "Cold application",
    app.referral ? "Referral / warm intro" : null,
  ].filter(Boolean) as string[];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="job-detail-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/75 backdrop-blur-[2px]"
        aria-label="Close modal"
        onClick={onClose}
      />

      <div className="relative w-full max-w-3xl max-h-[92vh] overflow-hidden rounded-xl border border-slate-600/60 bg-slate-900 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.65)] flex flex-col">
        {/* Top accent bar */}
        <div className="h-1 w-full bg-gradient-to-r from-indigo-600 via-sky-500 to-indigo-600 shrink-0" />

        {/* Header */}
        <div className="shrink-0 border-b border-slate-700/80 bg-slate-900/95 px-5 sm:px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${stageStyles(
                    app.stage
                  )}`}
                >
                  {stageLabel(app.stage)}
                </span>
                {app.source ? (
                  <span className="inline-flex items-center rounded-full bg-slate-800 px-2.5 py-0.5 text-[11px] font-medium text-slate-300 ring-1 ring-slate-600/80">
                    {display(app.source).replace(/\b\w/g, (c) =>
                      c.toUpperCase()
                    )}
                  </span>
                ) : null}
              </div>

              <h2
                id="job-detail-title"
                className="text-xl sm:text-[1.35rem] font-semibold text-white tracking-tight leading-snug"
              >
                {display(app.role_title, "Untitled role")}
              </h2>
              <p className="mt-1 text-sm font-medium text-slate-300">
                {display(app.company, "Unknown company")}
                {display(app.location) !== "—" ? (
                  <span className="text-slate-500 font-normal">
                    {" "}
                    · {display(app.location)}
                  </span>
                ) : null}
              </p>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-lg border border-slate-600 bg-slate-800/80 hover:bg-slate-700 text-slate-200 px-3 py-1.5 text-xs font-semibold transition-colors"
            >
              Close
            </button>
          </div>

          {app.job_url ? (
            <a
              href={app.job_url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex max-w-full items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300"
            >
              <span className="font-medium text-slate-500 shrink-0">
                Posting
              </span>
              <span className="truncate underline-offset-2 hover:underline">
                {app.job_url}
              </span>
            </a>
          ) : null}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-5 sm:px-6 py-5 space-y-6">
          {/* Summary panel */}
          <section className="rounded-lg border border-slate-700/70 bg-slate-950/35 p-4">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400 mb-3">
              Application summary
            </h3>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
              <MetaItem label="Compensation">
                {display(app.salary_range)}
              </MetaItem>
              <MetaItem label="Applied">
                {formatWhen(app.applied_at || app.applied_date)}
              </MetaItem>
              <MetaItem label="Target resume">
                {display(app.resume_target_role)}
              </MetaItem>
              <MetaItem label="Record created">
                {formatWhen(app.created_at)}
              </MetaItem>
              <MetaItem label="Last updated">
                {formatWhen(app.updated_at)}
              </MetaItem>
              <MetaItem label="Applied date">
                {formatDateOnly(app.applied_date)}
              </MetaItem>
            </dl>

            {flagChips.length > 0 ? (
              <div className="mt-4 pt-3 border-t border-slate-700/60 flex flex-wrap gap-2">
                {flagChips.map((chip) => (
                  <span
                    key={chip}
                    className="inline-flex items-center rounded-md bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300 ring-1 ring-slate-600/70"
                  >
                    {chip}
                  </span>
                ))}
              </div>
            ) : null}
          </section>

          {app.notes ? (
            <ContentBlock title="Internal notes" body={app.notes} />
          ) : null}

          {app.rejection_reason ? (
            <section className="rounded-lg border border-rose-900/40 bg-rose-950/20">
              <header className="border-b border-rose-900/30 px-4 py-2.5">
                <h4 className="text-[11px] font-semibold uppercase tracking-[0.07em] text-rose-300/90">
                  Rejection reason
                </h4>
              </header>
              <div className="px-4 py-3 text-[13px] leading-relaxed text-rose-100/90 whitespace-pre-wrap break-words">
                {display(app.rejection_reason)}
              </div>
            </section>
          ) : null}

          {app.linkedin_details ? (
            <LinkedInBlock details={app.linkedin_details} />
          ) : (
            <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/30 px-4 py-6 text-center">
              <p className="text-sm font-medium text-slate-300">
                No structured job posting data
              </p>
              <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                Re-fetch this application from the LinkedIn job URL to populate
                position details and hiring team contacts.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t border-slate-700/80 bg-slate-900/95 px-5 sm:px-6 py-3 flex items-center justify-between gap-3">
          <p className="text-[11px] text-slate-500 truncate">
            ID{" "}
            <span className="font-mono text-slate-400">
              {app.id != null ? String(app.id) : "—"}
            </span>
          </p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-slate-100 hover:bg-white text-slate-900 px-4 py-2 text-xs font-semibold transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}