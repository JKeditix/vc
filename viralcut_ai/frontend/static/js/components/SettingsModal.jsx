window.ViralCut = window.ViralCut || {};

window.ViralCut.SettingsModal = function SettingsModal({ settings, onClose, onSave }) {
    const { useState } = React;
    const [apiKey, setApiKey] = useState('');
    const [geminiModel, setGeminiModel] = useState(settings?.gemini_model || 'gemini-2.5-flash');
    const [whisperModel, setWhisperModel] = useState(settings?.whisper_model || 'tiny');
    const [saving, setSaving] = useState(false);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const payload = {
                gemini_model: geminiModel,
                whisper_model: whisperModel,
            };
            if (apiKey.trim()) {
                payload.gemini_api_key = apiKey.trim();
            }
            await onSave(payload);
            onClose();
        } finally {
            setSaving(false);
        }
    };

    const statusBadge = (ok) => (
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${ok ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-red-950 text-red-300 border border-red-800'}`}>
            {ok ? 'Ready' : 'Missing'}
        </span>
    );

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <form
                onSubmit={handleSave}
                className="bg-[#0e1525] border border-slate-700 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl"
            >
                <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-white">AI & Processing Settings</h3>
                    <button type="button" onClick={onClose} className="text-xs text-slate-400 hover:text-white font-semibold">
                        Close
                    </button>
                </div>

                {/* Engine Diagnostics */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400">FFmpeg / FFprobe</span>
                        {statusBadge(settings?.ffmpeg_available)}
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400">Local Whisper (faster-whisper)</span>
                        {statusBadge(settings?.faster_whisper_available)}
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400">OpenCV Speaker Face Tracking</span>
                        {statusBadge(settings?.opencv_available)}
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400">Gemini API Key</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${settings?.has_gemini_api_key ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'}`}>
                            {settings?.has_gemini_api_key ? 'Configured (Hidden)' : 'Not Set'}
                        </span>
                    </div>
                </div>

                <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                        Gemini API Key (leave blank to keep existing)
                    </label>
                    <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="AIzaSy..."
                        autoComplete="off"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                        Stored in server memory only and never returned by API endpoints.
                    </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Gemini Model</label>
                        <select
                            value={geminiModel}
                            onChange={(e) => setGeminiModel(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                        >
                            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Whisper Model</label>
                        <select
                            value={whisperModel}
                            onChange={(e) => setWhisperModel(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
                        >
                            <option value="tiny">tiny (fastest)</option>
                            <option value="base">base (balanced)</option>
                            <option value="small">small (accurate)</option>
                        </select>
                    </div>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                    <button type="button" onClick={onClose} className="px-4 py-2 bg-slate-800 text-xs text-slate-300 rounded-xl font-semibold">
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={saving}
                        className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-xs text-white rounded-xl font-bold disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Settings'}
                    </button>
                </div>
            </form>
        </div>
    );
};
