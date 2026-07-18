import type { JobApplication, JobStage } from "../../types/jobs";
import { STAGES } from "../../types/jobs";

type Props = {
    apps: JobApplication[];
    loading?: boolean;
    onStageChange: (id: string, stage: JobStage) => void;
    onDelete: (id: string) => void;
    onSelect: (app: JobApplication) => void;
};

function formatApplied(a: JobApplication): string {
    if (a.applied_at) {
        const d = new Date(a.applied_at);
        if (!Number.isNaN(d.getTime())) {
            return d.toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
            });
        }
    }
    if (a.applied_date) return a.applied_date;
    return "";
}

export default function JobTable({
    apps,
    loading,
    onStageChange,
    onDelete,
    onSelect,
}: Props) {
    if (loading) {
        return (
            <div className="text-slate-500 text-sm">Loading applications...</div>
        );
    }

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-800 font-semibold text-sm">
                Applications ({apps.length})
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead className="text-left text-slate-400 border-b border-slate-800">
                        <tr>
                            <th className="p-3">Company</th>
                            <th className="p-3">Role</th>
                            <th className="p-3">Source</th>
                            <th className="p-3">Stage</th>
                            <th className="p-3">Flags</th>
                            <th className="p-3"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {apps.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="p-6 text-slate-500 text-center">
                                    No applications yet — log your first one.
                                </td>
                            </tr>
                        ) : (
                            apps.map((a) => {
                                const when = formatApplied(a);
                                return (
                                    <tr
                                        key={a.id}
                                        className="border-b border-slate-800/80 hover:bg-slate-800/50 cursor-pointer transition-colors"
                                        onClick={() => onSelect(a)}
                                    >
                                        <td className="p-3">
                                            <div className="font-medium text-slate-100">
                                                {a.company}
                                            </div>
                                            {a.job_url ? (
                                                <a
                                                    href={a.job_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="text-xs text-blue-400 hover:underline"
                                                    onClick={(e) => e.stopPropagation()}
                                                >
                                                    Job link
                                                </a>
                                            ) : null}
                                        </td>
                                        <td className="p-3">
                                            <div>{a.role_title}</div>
                                            <div className="text-xs text-slate-500">{a.location}</div>
                                            {when ? (
                                                <div className="text-xs text-slate-600">{when}</div>
                                            ) : null}
                                            {a.salary_range ? (
                                                <div className="text-xs text-slate-500">
                                                    {a.salary_range}
                                                </div>
                                            ) : null}
                                        </td>
                                        <td className="p-3 text-slate-300">{a.source}</td>
                                        <td className="p-3" onClick={(e) => e.stopPropagation()}>
                                            <select
                                                value={a.stage}
                                                onChange={(e) =>
                                                    onStageChange(a.id, e.target.value as JobStage)
                                                }
                                                className="bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-xs text-white"
                                            >
                                                {STAGES.map((s) => (
                                                    <option key={s} value={s}>
                                                        {s}
                                                    </option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="p-3 text-xs text-slate-400">
                                            {a.tailored ? "tailored" : "cold"}
                                            {a.referral ? " · referral" : ""}
                                        </td>
                                        <td className="p-3" onClick={(e) => e.stopPropagation()}>
                                            <button
                                                type="button"
                                                onClick={() => onDelete(a.id)}
                                                className="text-xs text-red-400 hover:text-red-300"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}