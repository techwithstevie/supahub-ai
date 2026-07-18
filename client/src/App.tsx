import { useState } from "react";
import GitHubInput from "./components/GitHubInput";
import ResumePreview from "./components/ResumePreview";
import AgentStatus from "./components/AgentStatus";
import ResumeEditor from "./components/ResumeEditor";
import SectionRefiner from "./components/SectionRefiner";
import type { GenerateForm } from "./components/GitHubInput";
import type { ResumeDocument, ResumeSection } from "./types/resume";
import { emptyResume } from "./types/resume";

type Mode = "preview" | "edit";

export default function App() {
  const [resume, setResume] = useState<ResumeDocument>(emptyResume());
  const [html, setHtml] = useState("");
  const [markdown, setMarkdown] = useState("");
  const [agentLog, setAgentLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [refining, setRefining] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>("preview");
  const [hasResume, setHasResume] = useState(false);

  const applyPayload = (data: {
    resume?: ResumeDocument;
    resume_html?: string;
    resume_markdown?: string;
    agent_log?: string[];
  }) => {
    if (data.resume) setResume(data.resume);
    setHtml(data.resume_html || "");
    setMarkdown(data.resume_markdown || "");
    if (data.agent_log?.length) {
      setAgentLog((prev) => [...prev, ...data.agent_log!]);
    }
    setHasResume(true);
  };

  const handleGenerate = async (formData: GenerateForm) => {
    setLoading(true);
    setError("");
    setAgentLog([]);
    setHtml("");
    setMarkdown("");
    setHasResume(false);
    setMode("preview");

    try {
      const res = await fetch("/api/generate-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_username: formData.github_username.trim(),
          github_token: formData.github_token.trim() || null,
          full_name: formData.full_name.trim() || null,
          email: formData.email.trim() || null,
          phone: formData.phone.trim() || null,
          linkedin: formData.linkedin.trim() || null,
          portfolio: formData.portfolio.trim() || null,
          target_role:
            formData.target_role.trim() || "Senior Software Engineer",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
        );
      }
      applyPayload(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRefineSection = async (
    section: ResumeSection,
    prompt: string
  ) => {
    if (!hasResume) return;
    setRefining(true);
    setError("");
    try {
      const res = await fetch("/api/refine-section", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume, section, prompt }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
        );
      }
      applyPayload(data);
      setMode("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refine failed");
    } finally {
      setRefining(false);
    }
  };

  const handleSaveManual = async (next: ResumeDocument) => {
    setSaving(true);
    setError("");
    try {
      const res = await fetch("/api/update-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume: next }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`
        );
      }
      applyPayload(data);
      setMode("preview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 px-6 py-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">
            SH
          </div>
          <h1 className="text-xl font-semibold tracking-tight">
            SupaHub <span className="text-blue-400">AI</span>
          </h1>
        </div>
        {hasResume && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode("preview")}
              className={`text-xs px-3 py-1.5 rounded-lg ${mode === "preview"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-300"
                }`}
            >
              Preview
            </button>
            <button
              type="button"
              onClick={() => setMode("edit")}
              className={`text-xs px-3 py-1.5 rounded-lg ${mode === "edit"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-300"
                }`}
            >
              Manual Edit
            </button>
          </div>
        )}
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
          {hasResume && (
            <SectionRefiner
              disabled={loading || refining || saving}
              refining={refining}
              onRefine={handleRefineSection}
            />
          )}
        </div>

        <div className="space-y-4">
          {mode === "preview" ? (
            <ResumePreview
              html={html}
              markdown={markdown}
              loading={loading || refining}
            />
          ) : (
            <ResumeEditor
              resume={resume}
              saving={saving}
              onSave={handleSaveManual}
              onCancel={() => setMode("preview")}
            />
          )}
        </div>
      </main>
    </div>
  );
}