import type { JobAnalysis } from "../../types/jobs";

type Props = { analysis: JobAnalysis };

function List({ title, items }: { title: string; items: string[] }) {
    if (!items?.length) return null;
    return (
        <div>
            <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-2">
                {title}
            </h4>
            <ul className="space-y-1.5">
                {items.map((item, i) => (
                    <li key={i} className="text-sm text-slate-200 flex gap-2">
                        <span className="text-emerald-400">•</span>
                        <span>{item}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default function JobInsights({ analysis }: Props) {
    const scores = Object.entries(analysis.priority_score || {});

    return (
        <div className="bg-gradient-to-br from-slate-900 to-slate-900 border border-emerald-800/50 rounded-2xl p-5 space-y-5">
            <div>
                <h3 className="font-semibold text-emerald-400">Agent diagnosis</h3>
                <p className="text-sm text-slate-200 mt-2 leading-relaxed">
                    {analysis.diagnosis}
                </p>
            </div>

            {scores.length > 0 && (
                <div>
                    <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-2">
                        Health scores (higher = stronger)
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {scores.map(([k, v]) => (
                            <div
                                key={k}
                                className="bg-slate-800/80 rounded-lg px-3 py-2 text-xs"
                            >
                                <div className="text-slate-400">{k.replace(/_/g, " ")}</div>
                                <div className="text-lg font-semibold">{v}</div>
                                <div className="h-1.5 bg-slate-700 rounded mt-1 overflow-hidden">
                                    <div
                                        className={`h-full rounded ${v >= 70
                                                ? "bg-emerald-500"
                                                : v >= 40
                                                    ? "bg-amber-500"
                                                    : "bg-red-500"
                                            }`}
                                        style={{ width: `${Math.min(100, Math.max(0, v))}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <List title="Root causes" items={analysis.root_causes} />
                <List title="Strengths" items={analysis.strengths} />
                <List title="Action plan" items={analysis.action_plan} />
                <List
                    title="Resume recommendations"
                    items={analysis.resume_recommendations}
                />
                <List
                    title="Outreach recommendations"
                    items={analysis.outreach_recommendations}
                />
            </div>
        </div>
    );
}