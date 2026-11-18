const { useState, useEffect } = React;
const { api, Header, InputPanel, ProgressCard, ClipCard, ClipEditorModal, SettingsModal, formatTime } = window.ViralCut;

function App() {
    const [projects, setProjects] = useState([]);
    const [selectedProjectId, setSelectedProjectId] = useState(null);
    const [settings, setSettings] = useState(null);
    const [busy, setBusy] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');
    const [showSettings, setShowSettings] = useState(false);
    const [editingClip, setEditingClip] = useState(null);
    const [cacheBust, setCacheBust] = useState({});
    const [transcriptData, setTranscriptData] = useState(null);
    const [showTranscript, setShowTranscript] = useState(false);

    const loadProjects = async () => {
        try {
            const list = await api.listProjects();
            setProjects(list);
            setSelectedProjectId((current) => {
                if (current && list.some((p) => p.id === current)) return current;
                return list.length > 0 ? list[0].id : null;
            });
        } catch (err) {
            console.error(err);
        }
    };

    const loadSettings = async () => {
        try {
            const s = await api.getSettings();
            setSettings(s);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        loadProjects();
        loadSettings();
        const timer = setInterval(loadProjects, 2500);
        return () => clearInterval(timer);
    }, []);

    const activeProject = projects.find((p) => p.id === selectedProjectId) || projects[0] || null;

    useEffect(() => {
        setShowTranscript(false);
        setTranscriptData(null);
    }, [selectedProjectId]);

    const handleSubmitUrl = async (payload) => {
        setBusy(true);
        setErrorMsg('');
        try {
            const created = await api.createFromUrl(payload);
            setSelectedProjectId(created.id);
            await loadProjects();
        } catch (err) {
            setErrorMsg(err.message);
        } finally {
            setBusy(false);
        }
    };

    const handleUploadFile = async (payload) => {
        setBusy(true);
        setErrorMsg('');
        try {
            const created = await api.createFromUpload(payload);
            setSelectedProjectId(created.id);
            await loadProjects();
        } catch (err) {
            setErrorMsg(err.message);
        } finally {
            setBusy(false);
        }
    };

    const handleSaveRender = async (clipId, options) => {
        setErrorMsg('');
        try {
            await api.renderClip(clipId, options);
            setCacheBust((prev) => ({ ...prev, [clipId]: Date.now() }));
            await loadProjects();
        } catch (err) {
            setErrorMsg(err.message);
            throw err;
        }
    };

    const handleDeleteProject = async (projectId) => {
        if (!window.confirm('Delete this project and all generated clips from storage?')) return;
        setErrorMsg('');
        try {
            await api.deleteProject(projectId);
            await loadProjects();
        } catch (err) {
            setErrorMsg(err.message);
        }
    };

    const handleRetryProject = async (projectId) => {
        setErrorMsg('');
        try {
            await api.retryProject(projectId);
            await loadProjects();
        } catch (err) {
            setErrorMsg(err.message);
        }
    };

    const handleToggleTranscript = async () => {
        if (!activeProject) return;
        if (showTranscript) {
            setShowTranscript(false);
            return;
        }
        try {
            const data = await api.getTranscript(activeProject.id);
            setTranscriptData(data);
            setShowTranscript(true);
        } catch (err) {
            setErrorMsg(err.message);
        }
    };

    const handleSaveSettings = async (payload) => {
        setErrorMsg('');
        try {
            const updated = await api.updateSettings(payload);
            setSettings(updated);
        } catch (err) {
            setErrorMsg(err.message);
        }
    };

    return (
        <div className="min-h-screen flex flex-col">
            <Header settings={settings} onOpenSettings={() => setShowSettings(true)} />

            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
                {/* Hero */}
                <div className="text-center max-w-2xl mx-auto space-y-2">
                    <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white">
                        Turn Long Videos Into <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">Viral Shorts & Reels</span>
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-400">
                        Real FFmpeg editing, Whisper transcription, OpenCV face tracking, animated word subtitles, and Gemini AI virality scoring.
                    </p>
                </div>

                {errorMsg && (
                    <div className="bg-red-950/70 border border-red-800 text-red-200 rounded-xl px-4 py-3 text-xs flex items-center justify-between gap-4">
                        <span>{errorMsg}</span>
                        <button onClick={() => setErrorMsg('')} className="font-bold text-red-300 hover:text-white">
                            Dismiss
                        </button>
                    </div>
                )}

                <InputPanel onSubmitUrl={handleSubmitUrl} onUploadFile={handleUploadFile} busy={busy} />

                {/* Project History Switcher */}
                {projects.length > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2 overflow-x-auto pb-1">
                            <span className="text-xs font-bold text-slate-400 shrink-0">Projects:</span>
                            {projects.map((p) => (
                                <button
                                    key={p.id}
                                    onClick={() => setSelectedProjectId(p.id)}
                                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold border shrink-0 transition-colors ${
                                        activeProject && activeProject.id === p.id
                                            ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200'
                                            : 'bg-slate-900/90 border-slate-800 text-slate-400 hover:text-white'
                                    }`}
                                >
                                    {p.title.slice(0, 34)}{p.title.length > 34 ? '...' : ''}
                                </button>
                            ))}
                        </div>

                        {activeProject && (
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={handleToggleTranscript}
                                    className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200"
                                >
                                    {showTranscript ? 'Hide Transcript' : 'View Transcript'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleDeleteProject(activeProject.id)}
                                    className="px-3 py-1.5 rounded-xl bg-red-950/60 hover:bg-red-900/60 border border-red-800/70 text-xs font-semibold text-red-300"
                                >
                                    Delete Project
                                </button>
                            </div>
                        )}
                    </div>
                )}

                <ProgressCard project={activeProject} onRetry={handleRetryProject} />

                {/* Transcript Drawer */}
                {showTranscript && transcriptData && (
                    <section className="studio-card rounded-2xl p-5 space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-bold text-white">
                                Transcript <span className="text-xs font-normal text-slate-400">({transcriptData.engine})</span>
                            </h3>
                            <span className="text-[11px] text-slate-400">{transcriptData.segments?.length || 0} segment(s)</span>
                        </div>
                        {transcriptData.note && <p className="text-xs text-amber-300/90">{transcriptData.note}</p>}
                        <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                            {(transcriptData.segments || []).map((seg, i) => (
                                <div key={i} className="text-xs bg-slate-950/70 border border-slate-800/80 rounded-lg px-3 py-2 flex gap-3">
                                    <span className="font-mono text-indigo-400 shrink-0">
                                        {formatTime(seg.start)} - {formatTime(seg.end)}
                                    </span>
                                    <span className="text-slate-200">{seg.text || '[Active audio segment]'}</span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Clip Gallery */}
                {activeProject && activeProject.clips && activeProject.clips.length > 0 && (
                    <section className="space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                            <div>
                                <h2 className="text-lg font-extrabold text-white">
                                    Generated Clips ({activeProject.clips.length})
                                </h2>
                                <p className="text-xs text-slate-400">
                                    Source: {activeProject.title} &bull; {activeProject.width}x{activeProject.height} &bull; {Number(activeProject.duration || 0).toFixed(1)}s &bull; Engine: {activeProject.transcription_engine}
                                </p>
                            </div>

                            <a
                                href={`/api/clips/project/${activeProject.id}/download-all`}
                                className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-500/20"
                            >
                                Download All Clips (ZIP)
                            </a>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {activeProject.clips.map((clip) => (
                                <ClipCard
                                    key={clip.id}
                                    clip={clip}
                                    cacheBust={cacheBust[clip.id]}
                                    onEdit={(c) => setEditingClip(c)}
                                />
                            ))}
                        </div>
                    </section>
                )}
            </main>

            {editingClip && (
                <ClipEditorModal
                    clip={editingClip}
                    projectDuration={activeProject?.duration}
                    onClose={() => setEditingClip(null)}
                    onSaveRender={handleSaveRender}
                />
            )}

            {showSettings && (
                <SettingsModal
                    settings={settings}
                    onClose={() => setShowSettings(false)}
                    onSave={handleSaveSettings}
                />
            )}
        </div>
    );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
