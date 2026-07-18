import { useState } from "react";
import type { ResumeSection } from "../types/resume";

const SECTIONS: { id: ResumeSection; label: string; hint: string }[] = [
    { id: "header", label: "Header", hint: "Name, title, contact, tech line" },
    { id: "summary", label: "Summary", hint: "Professional blurb" },
    { id: "skills", label: "Skills", hint: "Categories and items" },
    { id: "experience", label: "Experience", hint: "Jobs and bullets" },
    { id: "projects", label: "Projects", hint: "Projects, stack, links" },
    { id: "education", label: "Education", hint: "Schools and credentials" },
];

type Props = {
    disabled?: boolean;
    refining?: boolean;
    onRefine: (section: ResumeSection, prompt: string) => void;
};

export default function SectionRefiner({
    disabled,
    refining,
    onRefine,
}: Props) {
    const [section, setSection] = useState<ResumeSection>("summary");
    const [prompt, setPrompt] = useState("");

    const hint = SECTIONS.find((s) => s.id === section)?.hint ?? "";

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            <div>
                <h2 className="text-lg font-semibold text-slate-100">
                    Refine a Section
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                    Tell the agent what to change. Only that section is rewritten.
                </p>
            </div>

            <div className="flex flex-wrap gap-2">
                {SECTIONS.map((s) => (
                    <button
                        key={s.id}
                        type="button"
                        disabled={disabled}
                        onClick={() => setSection(s.id)}
                        className={`text-xs px-3 py-1.5 rounded-full border transition ${section === s.id
                                ? "bg-blue-600 border-blue-500 text-white"
                                : "bg-slate-800 border-slate-600 text-slate-300 hover:border-slate-500"
                            }`}
                    >
                        {s.label}
                    </button>
                ))}
            </div>

            <p className="text-xs text-slate-500">{hint}</p>

            <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={disabled}
                rows={4}
                placeholder={
                    section === "experience"
                        ? "e.g. Make bullets more senior, emphasize React Native and CI/CD, keep dates."
                        : section === "summary"
                            ? "e.g. Tighten to 2 sentences, mention AI agents and mobile."
                            : "Describe the changes you want for this section..."
                }
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-y"
            />

            <button
                type="button"
                disabled={disabled || !prompt.trim()}
                onClick={() => onRefine(section, prompt.trim())}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl text-sm"
            >
                {refining ? "Agent refining..." : `Apply AI to ${section}`}
            </button>
        </div>
    );
}