window.ViralCut = window.ViralCut || {};

window.ViralCut.ProgressCard = function ProgressCard({ project, onRetry }) {
    if (!project || project.status === 'completed') return null;

    const isFailed = project.status === 'failed';
    const steps = [
        { label: 'Ingest', threshold: 10 },
        { label: 'Audio', threshold: 25 },
        { label: 'Transcribe', threshold: 45 },
        { label: 'AI Score', threshold: 65 },
        { label: 'Auto-Edit', threshold: 85 },
        { label: 'Ready', threshold: 100 },
    ];

    return (
        <section
            className={`rounded-2xl p-5 border space-y-4 ${
                isFailed
                    ? 'bg-red-950/35 border-red-800/80'
                    : 'studio-card border-indigo-500/30'
            }`}
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h3 className="font-bold text-sm text-white">{project.title}</h3>
                    <p className={`text-xs mt-0.5 ${isFailed ? 'text-red-300' : 'text-slate-400'}`}>
                        {project.status_message}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {isFailed && onRetry && (
                        <button
                            type="button"
                            onClick={() => onRetry(project.id)}
                            className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white transition-colors"
                        >
                            Resume / Retry
                        </button>
                    )}
                    <span
                        className={`font-mono text-xs font-bold px-3 py-1 rounded-full ${
                            isFailed
                                ? 'bg-red-900/60 text-red-200 border border-red-700'
                                : 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                        }`}
                    >
                        {isFailed ? 'FAILED' : `${project.progress}%`}
                    </span>
                </div>
            </div>

            {!isFailed && (
                <>
                    <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                        <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-500"
                            style={{ width: `${Math.max(4, project.progress)}%` }}
                        ></div>
                    </div>

                    <div className="grid grid-cols-6 gap-1.5 text-center">
                        {steps.map((step) => {
                            const done = project.progress >= step.threshold;
                            return (
                                <div
                                    key={step.label}
                                    className={`text-[10px] font-semibold py-1 rounded-md border ${
                                        done
                                            ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                                            : 'bg-slate-950/60 border-slate-800 text-slate-500'
                                    }`}
                                >
                                    {step.label}
                                </div>
                            );
                        })}
                    </div>
                </>
            )}
        </section>
    );
};
