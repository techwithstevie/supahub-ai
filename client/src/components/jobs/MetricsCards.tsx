import type { FunnelMetrics } from "../../types/jobs";

type Props = { metrics: FunnelMetrics; loading?: boolean };

function Card({
    label,
    value,
    sub,
    warn,
}: {
    label: string;
    value: string | number;
    sub?: string;
    warn?: boolean;
}) {
    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4">
            <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
            <div
                className={`text-2xl font-semibold mt-1 ${warn ? "text-amber-400" : "text-white"
                    }`}
            >
                {value}
            </div>
            {sub ? <div className="text-xs text-slate-500 mt-1">{sub}</div> : null}
        </div>
    );
}

export default function MetricsCards({ metrics, loading }: Props) {
    if (loading) {
        return <div className="text-slate-500 text-sm">Loading metrics...</div>;
    }

    const lowIv = metrics.applied_count >= 5 && metrics.interview_rate < 10;

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card
                label="Applications"
                value={metrics.applied_count}
                sub={`${metrics.total} tracked`}
            />
            <Card
                label="Response rate"
                value={`${metrics.response_rate}%`}
                sub={`${metrics.response_count} heard back`}
                warn={metrics.applied_count >= 5 && metrics.response_rate < 20}
            />
            <Card
                label="Interview rate"
                value={`${metrics.interview_rate}%`}
                sub={`${metrics.interview_count} interviews`}
                warn={lowIv}
            />
            <Card
                label="Offer rate"
                value={`${metrics.offer_rate}%`}
                sub={`${metrics.offer_count} offers`}
            />
            <Card
                label="Ghost rate"
                value={`${metrics.ghost_rate}%`}
                sub={`${metrics.ghosted_count} ghosted`}
                warn={metrics.ghost_rate > 40}
            />
            <Card
                label="Tailored → interview"
                value={`${metrics.tailored_interview_rate}%`}
                sub={`vs ${metrics.untailored_interview_rate}% cold apply`}
            />
            <Card
                label="Referral → interview"
                value={`${metrics.referral_interview_rate}%`}
                sub={`vs ${metrics.cold_interview_rate}% non-referral`}
            />
            <Card
                label="Avg days in pipeline"
                value={metrics.avg_days_in_pipeline}
                sub={
                    metrics.top_rejection_themes.length
                        ? `Themes: ${metrics.top_rejection_themes.join(", ")}`
                        : "No rejection themes yet"
                }
            />
        </div>
    );
}