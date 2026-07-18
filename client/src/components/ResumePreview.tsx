type Props = {
    html: string;
    markdown: string;
    loading: boolean;
};

export default function ResumePreview({ html, markdown, loading }: Props) {
    const printResume = () => {
        const w = window.open("", "_blank");
        if (!w) return;
        w.document.open();
        w.document.write(html);
        w.document.close();
        w.focus();
        setTimeout(() => w.print(), 300);
    };

    const copyMarkdown = async () => {
        try {
            await navigator.clipboard.writeText(markdown);
        } catch {
            /* ignore */
        }
    };

    return (
        <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 min-h-[640px] flex flex-col">
            <div className="flex items-center justify-between mb-3 px-1">
                <h2 className="text-lg font-semibold text-slate-100">Resume Preview</h2>
                <div className="flex gap-2">
                    {markdown ? (
                        <button
                            type="button"
                            onClick={copyMarkdown}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-slate-200"
                        >
                            Copy MD
                        </button>
                    ) : null}
                    {html ? (
                        <button
                            type="button"
                            onClick={printResume}
                            className="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg text-white font-medium"
                        >
                            Print / PDF
                        </button>
                    ) : null}
                </div>
            </div>

            {loading && (
                <div className="flex flex-col items-center justify-center flex-1 gap-3 text-slate-500">
                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-sm">Crafting recruiter-ready resume...</p>
                </div>
            )}

            {!loading && !html && (
                <div className="flex items-center justify-center flex-1 text-slate-600 text-sm">
                    Your professional resume will appear here
                </div>
            )}

            {!loading && html ? (
                <div className="flex-1 rounded-lg overflow-hidden border border-slate-600 bg-white">
                    <iframe
                        title="Resume"
                        srcDoc={html}
                        className="w-full h-[75vh] border-0 bg-white"
                        sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
                    />
                </div>
            ) : null}
        </div>
    );
}