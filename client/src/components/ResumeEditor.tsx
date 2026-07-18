import { useEffect, useState } from "react";
import type {
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeDocument,
    SkillCategory,
} from "../types/resume";

type Props = {
    resume: ResumeDocument;
    saving?: boolean;
    onSave: (resume: ResumeDocument) => void;
    onCancel: () => void;
};

function Field({
    label,
    value,
    onChange,
    multiline,
}: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    multiline?: boolean;
}) {
    const cls =
        "w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500";
    return (
        <div>
            <label className="block text-xs text-slate-400 mb-1">{label}</label>
            {multiline ? (
                <textarea
                    className={cls + " resize-y min-h-[80px]"}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                />
            ) : (
                <input
                    className={cls}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                />
            )}
        </div>
    );
}

export default function ResumeEditor({
    resume,
    saving,
    onSave,
    onCancel,
}: Props) {
    const [draft, setDraft] = useState<ResumeDocument>(resume);

    useEffect(() => {
        setDraft(resume);
    }, [resume]);

    const set = <K extends keyof ResumeDocument>(key: K, value: ResumeDocument[K]) =>
        setDraft((d) => ({ ...d, [key]: value }));

    const updateSkill = (i: number, patch: Partial<SkillCategory>) => {
        const skills = draft.skills.map((s, idx) =>
            idx === i ? { ...s, ...patch } : s
        );
        set("skills", skills);
    };

    const updateExp = (i: number, patch: Partial<ExperienceItem>) => {
        const experience = draft.experience.map((e, idx) =>
            idx === i ? { ...e, ...patch } : e
        );
        set("experience", experience);
    };

    const updateProj = (i: number, patch: Partial<ProjectItem>) => {
        const projects = draft.projects.map((p, idx) =>
            idx === i ? { ...p, ...patch } : p
        );
        set("projects", projects);
    };

    const updateEdu = (i: number, patch: Partial<EducationItem>) => {
        const education = draft.education.map((e, idx) =>
            idx === i ? { ...e, ...patch } : e
        );
        set("education", education);
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 max-h-[85vh] overflow-y-auto space-y-6">
            <div className="flex items-center justify-between sticky top-0 bg-slate-900 pb-3 z-10 border-b border-slate-800">
                <h2 className="text-lg font-semibold">Manual Edit</h2>
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="text-xs bg-slate-700 px-3 py-1.5 rounded-lg text-slate-200"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        disabled={saving}
                        onClick={() => onSave(draft)}
                        className="text-xs bg-blue-600 px-3 py-1.5 rounded-lg text-white font-medium disabled:opacity-50"
                    >
                        {saving ? "Saving..." : "Save & Re-render"}
                    </button>
                </div>
            </div>

            <section className="space-y-3">
                <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                    Header
                </h3>
                <Field label="Full name" value={draft.full_name} onChange={(v) => set("full_name", v)} />
                <Field label="Target title" value={draft.target_title} onChange={(v) => set("target_title", v)} />
                <Field label="Phone" value={draft.phone} onChange={(v) => set("phone", v)} />
                <Field label="Email" value={draft.email} onChange={(v) => set("email", v)} />
                <Field label="LinkedIn" value={draft.linkedin} onChange={(v) => set("linkedin", v)} />
                <Field label="GitHub" value={draft.github} onChange={(v) => set("github", v)} />
                <Field label="Portfolio" value={draft.portfolio} onChange={(v) => set("portfolio", v)} />
                <Field
                    label="Headline tech (comma-separated)"
                    value={draft.headline_tech.join(", ")}
                    onChange={(v) =>
                        set(
                            "headline_tech",
                            v.split(",").map((s) => s.trim()).filter(Boolean)
                        )
                    }
                />
            </section>

            <section className="space-y-3">
                <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                    Summary
                </h3>
                <Field
                    label="Summary"
                    multiline
                    value={draft.summary}
                    onChange={(v) => set("summary", v)}
                />
            </section>

            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                        Skills
                    </h3>
                    <button
                        type="button"
                        className="text-xs text-emerald-400"
                        onClick={() =>
                            set("skills", [
                                ...draft.skills,
                                { category: "New Category", items: [] },
                            ])
                        }
                    >
                        + Category
                    </button>
                </div>
                {draft.skills.map((sk, i) => (
                    <div key={i} className="border border-slate-700 rounded-xl p-3 space-y-2">
                        <Field
                            label="Category"
                            value={sk.category}
                            onChange={(v) => updateSkill(i, { category: v })}
                        />
                        <Field
                            label="Items (comma-separated)"
                            value={sk.items.join(", ")}
                            onChange={(v) =>
                                updateSkill(i, {
                                    items: v.split(",").map((s) => s.trim()).filter(Boolean),
                                })
                            }
                        />
                        <button
                            type="button"
                            className="text-xs text-red-400"
                            onClick={() =>
                                set(
                                    "skills",
                                    draft.skills.filter((_, idx) => idx !== i)
                                )
                            }
                        >
                            Remove category
                        </button>
                    </div>
                ))}
            </section>

            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                        Experience
                    </h3>
                    <button
                        type="button"
                        className="text-xs text-emerald-400"
                        onClick={() =>
                            set("experience", [
                                ...draft.experience,
                                {
                                    company: "",
                                    title: "",
                                    location: "Remote",
                                    start: "",
                                    end: "Present",
                                    bullets: [""],
                                    company_url: "",
                                },
                            ])
                        }
                    >
                        + Role
                    </button>
                </div>
                {draft.experience.map((ex, i) => (
                    <div key={i} className="border border-slate-700 rounded-xl p-3 space-y-2">
                        <Field label="Company" value={ex.company} onChange={(v) => updateExp(i, { company: v })} />
                        <Field label="Company URL" value={ex.company_url} onChange={(v) => updateExp(i, { company_url: v })} />
                        <Field label="Title" value={ex.title} onChange={(v) => updateExp(i, { title: v })} />
                        <div className="grid grid-cols-3 gap-2">
                            <Field label="Location" value={ex.location} onChange={(v) => updateExp(i, { location: v })} />
                            <Field label="Start" value={ex.start} onChange={(v) => updateExp(i, { start: v })} />
                            <Field label="End" value={ex.end} onChange={(v) => updateExp(i, { end: v })} />
                        </div>
                        <Field
                            label="Bullets (one per line)"
                            multiline
                            value={ex.bullets.join("\n")}
                            onChange={(v) =>
                                updateExp(i, {
                                    bullets: v.split("\n").map((s) => s.trim()).filter(Boolean),
                                })
                            }
                        />
                        <button
                            type="button"
                            className="text-xs text-red-400"
                            onClick={() =>
                                set(
                                    "experience",
                                    draft.experience.filter((_, idx) => idx !== i)
                                )
                            }
                        >
                            Remove role
                        </button>
                    </div>
                ))}
            </section>

            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                        Projects
                    </h3>
                    <button
                        type="button"
                        className="text-xs text-emerald-400"
                        onClick={() =>
                            set("projects", [
                                ...draft.projects,
                                {
                                    name: "",
                                    stack: [],
                                    links: [],
                                    bullets: [""],
                                    repo_url: "",
                                },
                            ])
                        }
                    >
                        + Project
                    </button>
                </div>
                {draft.projects.map((pr, i) => (
                    <div key={i} className="border border-slate-700 rounded-xl p-3 space-y-2">
                        <Field label="Name" value={pr.name} onChange={(v) => updateProj(i, { name: v })} />
                        <Field label="Repo URL" value={pr.repo_url} onChange={(v) => updateProj(i, { repo_url: v })} />
                        <Field
                            label="Stack (comma-separated)"
                            value={pr.stack.join(", ")}
                            onChange={(v) =>
                                updateProj(i, {
                                    stack: v.split(",").map((s) => s.trim()).filter(Boolean),
                                })
                            }
                        />
                        <Field
                            label="Links (Label|URL per line)"
                            multiline
                            value={pr.links.map((l) => `${l.label}|${l.url}`).join("\n")}
                            onChange={(v) =>
                                updateProj(i, {
                                    links: v
                                        .split("\n")
                                        .map((line) => line.trim())
                                        .filter(Boolean)
                                        .map((line) => {
                                            const [label, ...rest] = line.split("|");
                                            return {
                                                label: (label || "Link").trim(),
                                                url: rest.join("|").trim(),
                                            };
                                        }),
                                })
                            }
                        />
                        <Field
                            label="Bullets (one per line)"
                            multiline
                            value={pr.bullets.join("\n")}
                            onChange={(v) =>
                                updateProj(i, {
                                    bullets: v.split("\n").map((s) => s.trim()).filter(Boolean),
                                })
                            }
                        />
                        <button
                            type="button"
                            className="text-xs text-red-400"
                            onClick={() =>
                                set(
                                    "projects",
                                    draft.projects.filter((_, idx) => idx !== i)
                                )
                            }
                        >
                            Remove project
                        </button>
                    </div>
                ))}
            </section>

            <section className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wide">
                        Education
                    </h3>
                    <button
                        type="button"
                        className="text-xs text-emerald-400"
                        onClick={() =>
                            set("education", [
                                ...draft.education,
                                { school: "", credential: "", url: "", year: "" },
                            ])
                        }
                    >
                        + School
                    </button>
                </div>
                {draft.education.map((ed, i) => (
                    <div key={i} className="border border-slate-700 rounded-xl p-3 space-y-2">
                        <Field label="School" value={ed.school} onChange={(v) => updateEdu(i, { school: v })} />
                        <Field label="Credential" value={ed.credential} onChange={(v) => updateEdu(i, { credential: v })} />
                        <Field label="URL" value={ed.url} onChange={(v) => updateEdu(i, { url: v })} />
                        <Field label="Year" value={ed.year} onChange={(v) => updateEdu(i, { year: v })} />
                        <button
                            type="button"
                            className="text-xs text-red-400"
                            onClick={() =>
                                set(
                                    "education",
                                    draft.education.filter((_, idx) => idx !== i)
                                )
                            }
                        >
                            Remove
                        </button>
                    </div>
                ))}
            </section>
        </div>
    );
}