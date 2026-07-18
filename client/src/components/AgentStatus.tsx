export default function AgentStatus({ log }: { log: string[] }) {
    const icons: Record<string, string> = {
        "repo_analyst": "🔍",
        "skills_extractor": "🧠",
        "experience_writer": "✍️",
        "resume_assembler": "📄",
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Agent Pipeline</h3>
            <div className="space-y-2">
                {log.map((entry, i) => {
                    const key = entry.split(" ")[0];
                    return (
                        <div key={i} className="flex items-center gap-3 text-sm">
                            <span className="text-lg">{icons[key] || "🤖"}</span>
                            <span className="text-slate-300">{entry}</span>
                            <span className="ml-auto text-green-400 text-xs font-mono">DONE</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}