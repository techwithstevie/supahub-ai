import { useState } from "react";

export default function GitHubInput({ onGenerate, loading }: any) {
    const [form, setForm] = useState({
        github_username: "",
        github_token: "",
        full_name: "",
        email: "",
        phone: "",
        target_role: "Software Engineer",
    });

    const handle = (e: any) => setForm({ ...form, [e.target.name]: e.target.value });

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            <h2 className="text-lg font-semibold text-slate-100">Generate Your Resume</h2>
            <p className="text-sm text-slate-400">AI agents will analyze your GitHub and craft a recruiter-ready resume.</p>

            {[
                { name: "github_username", label: "GitHub Username *", placeholder: "techwithstevie" },
                { name: "github_token", label: "GitHub Token (optional, for private repos)", placeholder: "ghp_..." },
                { name: "full_name", label: "Full Name", placeholder: "Stephen Prahl" },
                { name: "email", label: "Email", placeholder: "stephen@example.com" },
                { name: "phone", label: "Phone", placeholder: "+1 (555) 000-0000" },
                { name: "target_role", label: "Target Role", placeholder: "Senior AI Engineer" },
            ].map(({ name, label, placeholder }) => (
                <div key={name}>
                    <label className="block text-xs text-slate-400 mb-1">{label}</label>
                    <input
                        name={name}
                        value={(form as any)[name]}
                        onChange={handle}
                        placeholder={placeholder}
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                </div>
            ))}

            <button
                onClick={() => onGenerate(form)}
                disabled={loading || !form.github_username}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl transition-all text-sm"
            >
                {loading ? "Agents Working..." : "⚡ Generate Resume"}
            </button>
        </div>
    );
}