import { useCallback, useEffect, useState } from "react";
import type {
    FunnelMetrics,
    JobAnalysis,
    JobApplication,
    JobStage,
} from "../types/jobs";
import MetricsCards from "../components/jobs/MetricsCards";
import JobForm from "../components/jobs/JobForm";
import JobTable from "../components/jobs/JobTable";
import JobInsights from "../components/jobs/JobInsights";

const emptyMetrics = (): FunnelMetrics => ({
    total: 0,
    by_stage: {},
    by_source: {},
    applied_count: 0,
    response_count: 0,
    interview_count: 0,
    offer_count: 0,
    rejected_count: 0,
    ghosted_count: 0,
    tailored_count: 0,
    referral_count: 0,
    response_rate: 0,
    interview_rate: 0,
    offer_rate: 0,
    ghost_rate: 0,
    tailored_interview_rate: 0,
    untailored_interview_rate: 0,
    referral_interview_rate: 0,
    cold_interview_rate: 0,
    avg_days_in_pipeline: 0,
    top_rejection_themes: [],
});

export default function JobTrackerPage() {
    const [apps, setApps] = useState<JobApplication[]>([]);
    const [metrics, setMetrics] = useState<FunnelMetrics>(emptyMetrics());
    const [analysis, setAnalysis] = useState<JobAnalysis | null>(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState("");
    const [focus, setFocus] = useState(
        "Why am I not landing interviews and what should I change this week?"
    );

    const refresh = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const res = await fetch("/api/jobs/metrics");
            const data = await res.json();
            if (!res.ok) {
                throw new Error(
                    typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
                );
            }
            setMetrics(data.metrics);
            setApps(data.applications || []);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to load jobs");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    const handleCreate = async (payload: Record<string, unknown>) => {
        const res = await fetch("/api/jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(
                typeof data.detail === "string" ? data.detail : "Create failed"
            );
        }
        await refresh();
    };

    const handleStageChange = async (id: string, stage: JobStage) => {
        const res = await fetch(`/api/jobs/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage }),
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            setError(
                typeof data.detail === "string" ? data.detail : "Update failed"
            );
            return;
        }
        await refresh();
    };

    const handleDelete = async (id: string) => {
        const res = await fetch(`/api/jobs/${id}`, { method: "DELETE" });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            setError(
                typeof data.detail === "string" ? data.detail : "Delete failed"
            );
            return;
        }
        await refresh();
    };

    const handleAnalyze = async () => {
        setAnalyzing(true);
        setError("");
        try {
            const res = await fetch("/api/jobs/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ focus, include_notes: true }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(
                    typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
                );
            }
            setAnalysis(data as JobAnalysis);
            if (data.metrics) setMetrics(data.metrics);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Analysis failed");
        } finally {
            setAnalyzing(false);
        }
    };

    return (
        <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-semibold">Job Search Tracker</h2>
                    <p className="text-slate-400 text-sm mt-1">
                        Log every application. Metrics expose the funnel. Agents diagnose
                        why interviews are not converting.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => void handleAnalyze()}
                    disabled={analyzing || apps.length === 0}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold px-5 py-3 rounded-xl text-sm"
                >
                    {analyzing
                        ? "Agents analyzing..."
                        : "Analyze why I’m not getting interviews"}
                </button>
            </div>

            {error && (
                <div className="rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-300">
                    {error}
                </div>
            )}

            <MetricsCards metrics={metrics} loading={loading} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 space-y-4">
                    <JobForm onCreate={handleCreate} />
                    <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 space-y-3">
                        <label className="text-xs text-slate-400" htmlFor="analysis-focus">
                            Analysis focus
                        </label>
                        <textarea
                            id="analysis-focus"
                            value={focus}
                            onChange={(e) => setFocus(e.target.value)}
                            rows={3}
                            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                        />
                    </div>
                </div>

                <div className="lg:col-span-2 space-y-6">
                    {analysis && <JobInsights analysis={analysis} />}
                    <JobTable
                        apps={apps}
                        loading={loading}
                        onStageChange={handleStageChange}
                        onDelete={handleDelete}
                    />
                </div>
            </div>
        </main>
    );
}