window.ViralCut = window.ViralCut || {};

window.ViralCut.ClipEditorModal = function ClipEditorModal({ clip, projectDuration, onClose, onSaveRender }) {
    const { useState } = React;

    const [startTime, setStartTime] = useState(Number(clip.start_time || 0));
    const [endTime, setEndTime] = useState(Number(clip.end_time || 15));
    const [aspectRatio, setAspectRatio] = useState(clip.aspect_ratio || '9:16');
    const [exportPreset, setExportPreset] = useState(clip.export_preset || 'youtube_shorts');
    const [removeSilence, setRemoveSilence] = useState(Boolean(clip.remove_silence));
    const [burnSubtitles, setBurnSubtitles] = useState(Boolean(clip.burn_subtitles));
    const [enableZoom, setEnableZoom] = useState(Boolean(clip.enable_zoom));
    const [enableFaceTracking, setEnableFaceTracking] = useState(Boolean(clip.enable_face_tracking));
    const [enableTransitions, setEnableTransitions] = useState(Boolean(clip.enable_transitions));
    const [enhanceAudio, setEnhanceAudio] = useState(Boolean(clip.enhance_audio));
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await onSaveRender(clip.id, {
                start_time: Number(startTime),
                end_time: Number(endTime),
                aspect_ratio: aspectRatio,
                export_preset: exportPreset,
                remove_silence: removeSilence,
                burn_subtitles: burnSubtitles,
                enable_zoom: enableZoom,
                enable_face_tracking: enableFaceTracking,
                enable_transitions: enableTransitions,
                enhance_audio: enhanceAudio,
            });
            onClose();
        } finally {
            setSaving(false);
        }
    };

    const toggles = [
        { label: 'Remove Silent Portions', value: removeSilence, set: setRemoveSilence },
        { label: 'Animated Word Subtitles', value: burnSubtitles, set: setBurnSubtitles },
        { label: 'Speaker Face Tracking', value: enableFaceTracking, set: setEnableFaceTracking },
        { label: 'Smooth Dynamic Zoom', value: enableZoom, set: setEnableZoom },
        { label: 'Smooth Transitions (xfade)', value: enableTransitions, set: setEnableTransitions },
        { label: 'Audio Enhancement (Denoise + Loudnorm)', value: enhanceAudio, set: setEnhanceAudio },
    ];

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <form
                onSubmit={handleSubmit}
                className="bg-[#0e1525] border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl"
            >
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h3 className="text-base font-bold text-white">Edit & Re-Render Clip</h3>
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{clip.ai_title || clip.title}</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-slate-400 hover:text-white text-sm font-bold"
                    >
                        Close
                    </button>
                </div>

                {/* Timestamps */}
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                            Start Time (seconds)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            max={projectDuration || undefined}
                            value={startTime}
                            onChange={(e) => setStartTime(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                            End Time (seconds)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0.5"
                            max={projectDuration || undefined}
                            value={endTime}
                            onChange={(e) => setEndTime(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                            required
                        />
                    </div>
                </div>

                {/* Format & Preset */}
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">Aspect Ratio</label>
                        <select
                            value={aspectRatio}
                            onChange={(e) => setAspectRatio(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                        >
                            <option value="9:16">9:16 Vertical (1080x1920)</option>
                            <option value="1:1">1:1 Square (1080x1080)</option>
                            <option value="16:9">16:9 Landscape (1920x1080)</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-[11px] font-semibold text-slate-400 mb-1">Platform Preset</label>
                        <select
                            value={exportPreset}
                            onChange={(e) => setExportPreset(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                        >
                            <option value="youtube_shorts">YouTube Shorts</option>
                            <option value="instagram_reels">Instagram Reels</option>
                            <option value="tiktok">TikTok</option>
                        </select>
                    </div>
                </div>

                {/* Effect Toggles */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {toggles.map((item) => (
                        <label
                            key={item.label}
                            className="flex items-center gap-2.5 bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 cursor-pointer"
                        >
                            <input
                                type="checkbox"
                                checked={item.value}
                                onChange={(e) => item.set(e.target.checked)}
                                className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
                            />
                            <span>{item.label}</span>
                        </label>
                    ))}
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={saving}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 rounded-xl font-semibold"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={saving}
                        className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs text-white rounded-xl font-bold disabled:opacity-50"
                    >
                        {saving ? 'Rendering with FFmpeg...' : 'Apply & Re-Render'}
                    </button>
                </div>
            </form>
        </div>
    );
};
