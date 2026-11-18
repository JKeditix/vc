window.ViralCut = window.ViralCut || {};

window.ViralCut.Header = function Header({ settings, onOpenSettings }) {
    const readyCount = [
        settings?.ffmpeg_available,
        settings?.faster_whisper_available,
        settings?.opencv_available,
    ].filter(Boolean).length;

    return (
        <header className="sticky top-0 z-30 h-16 border-b border-slate-800/80 bg-[#070b14]/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center font-black text-white shadow-lg shadow-indigo-500/20">
                    VC
                </div>
                <div>
                    <div className="flex items-center gap-2">
                        <span className="font-extrabold text-lg tracking-wider text-white">VIRALCUT AI</span>
                        <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                            Studio v2
                        </span>
                    </div>
                    <p className="text-[11px] text-slate-400 hidden sm:block">
                        Automated Shorts, Reels & TikTok Engine
                    </p>
                </div>
            </div>

            <div className="flex items-center gap-3">
                <div className="hidden md:flex items-center gap-2 text-[11px] text-slate-400 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-lg">
                    <span className={`w-2 h-2 rounded-full ${readyCount === 3 ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
                    <span>FFmpeg / Whisper / FaceTrack ({readyCount}/3)</span>
                </div>

                <button
                    onClick={onOpenSettings}
                    className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700/80 rounded-xl text-xs font-semibold text-slate-200 flex items-center gap-2 transition-colors"
                >
                    <span className={`w-2 h-2 rounded-full ${settings?.has_gemini_api_key ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
                    <span>AI Settings</span>
                </button>
            </div>
        </header>
    );
};
