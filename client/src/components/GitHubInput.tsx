import { useState } from "react";
import type { GenerateForm } from "../App";

type Props = {
    onGenerate: (form: GenerateForm) => void;
    loading: boolean;
};

export default function GitHubInput({ onGenerate, loading }: Props) {
    const [form, setForm] = useState<GenerateForm>({
        github_username: "",
        github_token: "",
        full_name: "",
        email: "",
        phone: "",
        target_role: "Software Engineer",
        linkedin: "",
        portfolio: "",
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const fields: {
        name: keyof GenerateForm;
        label: string;
        placeholder: string;
    }[] = [
            {
                name: "github_username",
                label: "GitHub Username *",
                placeholder: "techwithstevie",
            },
            {
                name: "github_token",
                label: "GitHub Token (optional)",
                placeholder: "ghp_...",
            },
            {
                name: "full_name",
                label: "Full Name",
                placeholder: "Stephen Prahl",
            },
            {
                name: "email",
                label: "Email",
                placeholder: "you@example.com",
            },
            {
                name: "phone",
                label: "Phone",
                placeholder: "+1 (555) 000-0000",
            },
            {
                name: "target_role",
                label: "Target Role",
                placeholder: "Senior AI Engineer",
            },
        ];

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            <div>
                <h2 className="text-lg font-semibold text-slate-100">
                    Generate Your Resume
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                    Agents analyze your GitHub and build a recruiter-ready resume.
                </p>
            </div>

            {fields.map(({ name, label, placeholder }) => (
                <div key={name}>
                    <label className="block text-xs text-slate-400 mb-1" htmlFor={name}>
                        {label}
                    </label>
                    <input
                        id={name}
                        name={name}
                        value={form[name]}
                        onChange={handleChange}
                        placeholder={placeholder}
                        autoComplete="off"
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                </div>
            ))}

            <button
                type="button"
                onClick={() => onGenerate(form)}
                disabled={loading || !form.github_username.trim()}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl transition-all text-sm"
            >
                {loading ? "Agents Working..." : "Generate Resume"}
            </button>
        </div>
    );
}