window.ViralCut = window.ViralCut || {};

window.ViralCut.InputPanel = function InputPanel({ onSubmitUrl, onUploadFile, busy }) {
    const { useState, useRef } = React;

    const [mode, setMode] = useState('upload');
    const [url, setUrl] = useState('');
    const [rightsConfirmed, setRightsConfirmed] = useState(true);
    const [targetClipDuration, setTargetClipDuration] = useState(30);
    const [maxClips, setMaxClips] = useState(6);
    const [aspectRatio, setAspectRatio] = useState('9:16');
    const [exportPreset, setExportPreset] = useState('youtube_shorts');
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef(null);

    const handleUrlForm = (e) => {
        e.preventDefault();
        if (!url.trim()) return;
        onSubmitUrl({
            url: url.trim(),
            rightsConfirmed,
            targetClipDuration,
            maxClips,
            aspectRatio,
            exportPreset,
        });
        setUrl('');
    };

    const triggerFile = (file) => {
        if (!file) return;
        onUploadFile({
            file,
            rightsConfirmed,
            targetClipDuration,
            maxClips,
            aspectRatio,
            exportPreset,
        });
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) triggerFile(file);
    };

    return (
        <section className="studio-card rounded-2xl p-5 sm:p-6 shadow-2xl space-y-5">
            {/* Mode Switcher */}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="inline-flex bg-slate-950 p-1 rounded-xl border border-slate-800">
                    <button
                        type="button"
                        onClick={() => setMode('upload')}
                        className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                            mode === 'upload'
                                ? 'bg-indigo-600 text-white shadow'
                                : 'text-slate-400 hover:text-white'
                        }`}
                    >
                        Upload Video (MP4 / MOV / WebM)
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode('url')}
                        className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                            mode === 'url'
                                ? 'bg-indigo-600 text-white shadow'
                                : 'text-slate-400 hover:text-white'
                        }`}
                    >
                        YouTube URL
                    </button>
                </div>

                <span className="text-[11px] text-slate-400">
                    Auto Face Track &bull; Silence Cut &bull; Word Subtitles &bull; Audio Boost
                </span>
            </div>

            {/* Generation Controls */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5">Target Clip Length</label>
                    <select
                        value={targetClipDuration}
                        onChange={(e) => setTargetClipDuration(Number(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    >
                        {[15, 30, 45, 60, 90].map((sec) => (
                            <option key={sec} value={sec}>{sec} seconds</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5">Clips to Generate</label>
                    <select
                        value={maxClips}
                        onChange={(e) => setMaxClips(Number(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    >
                        {[3, 5, 6, 8, 10].map((n) => (
                            <option key={n} value={n}>Up to {n} clips</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5">Aspect Ratio</label>
                    <select
                        value={aspectRatio}
                        onChange={(e) => setAspectRatio(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    >
                        <option value="9:16">9:16 Vertical (1080x1920)</option>
                        <option value="1:1">1:1 Square (1080x1080)</option>
                        <option value="16:9">16:9 Landscape (1920x1080)</option>
                    </select>
                </div>

                <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1.5">Export Platform</label>
                    <select
                        value={exportPreset}
                        onChange={(e) => setExportPreset(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    >
                        <option value="youtube_shorts">YouTube Shorts</option>
                        <option value="instagram_reels">Instagram Reels</option>
                        <option value="tiktok">TikTok</option>
                    </select>
                </div>
            </div>

            {/* Active Input Area */}
            {mode === 'url' ? (
                <form onSubmit={handleUrlForm} className="flex flex-col sm:flex-row gap-3">
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="Paste YouTube video URL (https://www.youtube.com/watch?v=...)"
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                        required
                    />
                    <button
                        type="submit"
                        disabled={busy || !rightsConfirmed}
                        className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-bold rounded-xl text-sm shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition-all"
                    >
                        {busy ? 'Starting...' : 'Generate Viral Shorts'}
                    </button>
                </form>
            ) : (
                <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => !busy && rightsConfirmed && fileInputRef.current?.click()}
                    className={`border-2 border-dashed border-slate-700/80 rounded-2xl p-8 text-center cursor-pointer transition-all hover:border-indigo-500/70 bg-slate-950/50 ${
                        dragOver ? 'dropzone-active' : ''
                    } ${busy || !rightsConfirmed ? 'opacity-50 pointer-events-none' : ''}`}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
                        className="hidden"
                        onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) triggerFile(f);
                            e.target.value = '';
                        }}
                    />
                    <p className="text-sm font-bold text-white">
                        {busy ? 'Uploading & Initializing Pipeline...' : 'Drag & drop a video file here, or click to browse'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                        Supports MP4, MOV, and WebM &bull; Automatic speech analysis, face tracking & vertical export
                    </p>
                </div>
            )}

            {/* Rights Confirmation */}
            <label className="flex items-start gap-2.5 text-xs text-slate-400 cursor-pointer select-none">
                <input
                    type="checkbox"
                    checked={rightsConfirmed}
                    onChange={(e) => setRightsConfirmed(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                />
                <span>
                    I confirm that I own this video or have explicit permission to process and repurpose it.
                </span>
            </label>
        </section>
    );
};
