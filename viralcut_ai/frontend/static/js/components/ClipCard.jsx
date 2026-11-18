window.ViralCut = window.ViralCut || {};

window.ViralCut.ClipCard = function ClipCard({ clip, cacheBust, onEdit }) {
    const { useState } = React;
    const [copiedField, setCopiedField] = useState('');
    const [showCopyDetails, setShowCopyDetails] = useState(false);

    const fmt = window.ViralCut.formatTime;

    const copyText = async (label, value) => {
        if (!value) return;
        try {
            await navigator.clipboard.writeText(value);
            setCopiedField(label);
            setTimeout(() => setCopiedField(''), 1500);
        } catch (_err) {
            // Ignore clipboard errors in non-HTTPS contexts
        }
    };

    const scoreColor =
        clip.virality_score >= 85
            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/70'
            : clip.virality_score >= 70
            ? 'bg-amber-950/80 text-amber-300 border-amber-700/70'
            : 'bg-slate-900 text-slate-300 border-slate-700';

    const presetLabel = {
        youtube_shorts: 'YouTube Shorts',
        instagram_reels: 'Instagram Reels',
        tiktok: 'TikTok',
    }[clip.export_preset] || clip.export_preset;

    const bust = cacheBust || 0;

    return (
        <article className="studio-card rounded-2xl overflow-hidden flex flex-col justify-between hover:border-indigo-500/50 transition-all shadow-xl">
            {/* Top Badges & Video Preview */}
            <div>
                <div className="px-4 pt-4 pb-3 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                        <span className={`text-[11px] font-extrabold px-2.5 py-1 rounded-full border ${scoreColor}`}>
                            Score {clip.virality_score}/100
                        </span>
                        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/70">
                            {clip.category}
                        </span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                        {fmt(clip.start_time)} - {fmt(clip.end_time)}
                    </span>
                </div>

                {/* Video Player / Thumbnail */}
                <div className="px-4">
                    <div className="relative rounded-xl overflow-hidden bg-black border border-slate-800 aspect-[9/16] max-h-80 flex items-center justify-center">
                        {clip.rendered && clip.media_url ? (
                            <video
                                key={`${clip.id}-${bust}`}
                                src={`${clip.media_url}?v=${bust}`}
                                poster={clip.thumbnail_url ? `${clip.thumbnail_url}?v=${bust}` : undefined}
                                controls
                                preload="metadata"
                                className="w-full h-full object-contain bg-black"
                            />
                        ) : (
                            <div className="p-4 text-center space-y-2">
                                <p className="text-xs font-semibold text-slate-400">
                                    {clip.render_error ? 'Render failed' : 'Clip not rendered yet'}
                                </p>
                                {clip.render_error && (
                                    <p className="text-[11px] text-red-400 line-clamp-3">{clip.render_error}</p>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Metadata & AI Copywriting */}
                <div className="p-4 space-y-3">
                    <div>
                        <h3 className="font-bold text-sm text-white leading-snug">{clip.ai_title || clip.title}</h3>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{clip.summary}</p>
                        {clip.virality_reason && (
                            <p className="text-[11px] text-emerald-400/90 mt-1">{clip.virality_reason}</p>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-1.5 text-[10px] font-semibold text-slate-300">
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">{clip.aspect_ratio}</span>
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">{presetLabel}</span>
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                            {Number(clip.rendered_duration || clip.duration || 0).toFixed(1)}s
                        </span>
                        {clip.remove_silence && <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">No Silence</span>}
                        {clip.burn_subtitles && <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">Subtitles</span>}
                        {clip.enable_face_tracking && <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800">FaceTrack</span>}
                    </div>

                    {/* Expandable AI Content Block */}
                    <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 space-y-2 text-[11px]">
                        <div className="flex items-center justify-between">
                            <span className="font-bold text-indigo-300 uppercase tracking-wider text-[10px]">
                                AI Copy & Thumbnail Idea
                            </span>
                            <button
                                type="button"
                                onClick={() => setShowCopyDetails(!showCopyDetails)}
                                className="text-[10px] text-slate-400 hover:text-white font-semibold"
                            >
                                {showCopyDetails ? 'Hide' : 'Expand'}
                            </button>
                        </div>

                        {clip.ai_hook && (
                            <p className="text-amber-300 font-medium">
                                <span className="text-slate-500">Hook: </span>"{clip.ai_hook}"
                            </p>
                        )}
                        <p className="text-cyan-300/90 break-words">{clip.ai_hashtags}</p>

                        {showCopyDetails && (
                            <div className="pt-2 border-t border-slate-800 space-y-2">
                                {clip.ai_description && (
                                    <p className="text-slate-300 whitespace-pre-line">{clip.ai_description}</p>
                                )}
                                {clip.thumbnail_suggestion && (
                                    <p className="text-slate-400">
                                        <span className="text-slate-200 font-semibold">Thumbnail: </span>
                                        {clip.thumbnail_suggestion}
                                    </p>
                                )}
                                <button
                                    type="button"
                                    onClick={() =>
                                        copyText(
                                            'all',
                                            `${clip.ai_title || clip.title}\n\n${clip.ai_description || ''}\n\n${clip.ai_hashtags || ''}`
                                        )
                                    }
                                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-[10px] font-semibold text-white"
                                >
                                    {copiedField === 'all' ? 'Copied!' : 'Copy Title + Caption + Hashtags'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Footer Action Buttons */}
            <div className="px-4 pb-4 flex items-center gap-2">
                <button
                    type="button"
                    onClick={() => onEdit(clip)}
                    className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold text-xs rounded-xl transition-colors"
                >
                    Edit & Re-Render
                </button>
                {clip.rendered ? (
                    <a
                        href={`/api/clips/${clip.id}/download`}
                        download
                        className="flex-1 text-center py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition-colors shadow-lg shadow-indigo-600/20"
                    >
                        Download MP4
                    </a>
                ) : (
                    <button
                        type="button"
                        onClick={() => onEdit(clip)}
                        className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl"
                    >
                        Render Now
                    </button>
                )}
            </div>
        </article>
    );
};
