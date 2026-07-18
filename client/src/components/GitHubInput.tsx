import { useState } from "react";

export type GenerateForm = {
    github_username: string;
    github_token: string;
    full_name: string;
    email: string;
    phone: string;
    linkedin: string;
    portfolio: string;
    target_role: string;
};

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
        linkedin: "",
        portfolio: "",
        target_role: "Senior Software Engineer",
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
            { name: "github_username", label: "GitHub Username *", placeholder: "techwithstevie" },
            { name: "github_token", label: "GitHub Token (optional)", placeholder: "ghp_..." },
            { name: "full_name", label: "Full Name", placeholder: "Stephen Prahl" },
            { name: "email", label: "Email", placeholder: "you@example.com" },
            { name: "phone", label: "Phone", placeholder: "732-575-9802" },
            { name: "linkedin", label: "LinkedIn", placeholder: "https://linkedin.com/in/you" },
            { name: "portfolio", label: "Portfolio URL", placeholder: "https://stephenprahl.vercel.app" },
            { name: "target_role", label: "Target Role", placeholder: "Senior Software Engineer" },
        ];

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-4">
            <div>
                <h2 className="text-lg font-semibold text-slate-100">Generate Your Resume</h2>
                <p className="text-sm text-slate-400 mt-1">
                    Then refine any section with AI or edit manually.
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
                        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                </div>
            ))}
            <button
                type="button"
                onClick={() => onGenerate(form)}
                disabled={loading || !form.github_username.trim()}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl text-sm"
            >
                {loading ? "Agents Working..." : "Generate Resume"}
            </button>
        </div>
    );
}