import ReactMarkdown from "react-markdown";

type Props = {
    markdown: string;
    loading: boolean;
};

export default function ResumePreview({ markdown, loading }: Props) {
    const copyToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(markdown);
        } catch {
            // ignore clipboard failures
        }
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 min-h-[600px]">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-100">Resume Preview</h2>
                {markdown ? (
                    <button
                        type="button"
                        onClick={copyToClipboard}
                        className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-slate-300 transition"
                    >
                        Copy Markdown
                    </button>
                ) : null}
            </div>

            {loading && (
                <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500">
                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm">Agents analyzing your GitHub...</p>
                </div>
            )}

            {!loading && !markdown && (
                <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
                    Your resume will appear here
                </div>
            )}

            {!loading && markdown ? (
                <div className="bg-white text-slate-900 rounded-xl p-6 overflow-auto max-h-[75vh] prose prose-sm max-w-none">
                    <ReactMarkdown>{markdown}</ReactMarkdown>
                </div>
            ) : null}
        </div>
    );
}