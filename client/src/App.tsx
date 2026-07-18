import { useState } from "react";
import GitHubInput from "./components/GitHubInput";
import ResumePreview from "./components/ResumePreview";
import AgentStatus from "./components/AgentStatus";

export default function App() {
  const [resume, setResume] = useState<string>("");
  const [agentLog, setAgentLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (formData: any) => {
    setLoading(true);
    setResume("");
    setAgentLog([]);
    try {
      const res = await fetch("http://localhost:8000/generate-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setResume(data.resume_markdown);
      setAgentLog(data.agent_log);
    } catch (err) {
      alert("Error generating resume. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <header className="border-b border-slate-800 px-8 py-5 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">RF</div>
        <h1 className="text-xl font-semibold tracking-tight">ResumeForge <span className="text-blue-400">AI</span></h1>
      </header>

      <main className="max-w-7xl mx-auto px-8 py-10 grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="space-y-6">
          <GitHubInput onGenerate={handleGenerate} loading={loading} />
          {agentLog.length > 0 && <AgentStatus log={agentLog} />}
        </div>
        <ResumePreview markdown={resume} loading={loading} />
      </main>
    </div>
  );
}