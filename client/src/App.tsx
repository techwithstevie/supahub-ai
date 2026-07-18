import { useState } from "react";
import GitHubInput from "./components/GitHubInput";
import ResumePreview from "./components/ResumePreview";
import AgentStatus from "./components/AgentStatus";

export type GenerateForm = {
  github_username: string;
  github_token: string;
  full_name: string;
  email: string;
  phone: string;
  target_role: string;
};

export default function App() {
  const [resume, setResume] = useState("");
  const [agentLog, setAgentLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async (formData: GenerateForm) => {
    setLoading(true);
    setResume("");
    setAgentLog([]);
    setError("");

    try {
      // Uses Vite proxy → http://127.0.0.1:8000/generate-resume
      const res = await fetch("/api/generate-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_username: formData.github_username.trim(),
          github_token: formData.github_token.trim() || null,
          full_name: formData.full_name.trim() || null,
          email: formData.email.trim() || null,
          phone: formData.phone.trim() || null,
          target_role: formData.target_role.trim() || "Software Engineer",
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d: { msg?: string }) => d.msg).join(", ")
              : `HTTP ${res.status}`;
        throw new Error(detail);
      }

      setResume(data.resume_markdown || "");
      setAgentLog(data.agent_log || []);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to generate resume";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 px-6 py-5 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">
          SH
        </div>
        <h1 className="text-xl font-semibold tracking-tight">
          SupaHub <span className="text-blue-400">AI</span>
        </h1>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <GitHubInput onGenerate={handleGenerate} loading={loading} />
          {error && (
            <div className="rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}
          {agentLog.length > 0 && <AgentStatus log={agentLog} />}
        </div>
        <ResumePreview markdown={resume} loading={loading} />
      </main>
    </div>
  );
}