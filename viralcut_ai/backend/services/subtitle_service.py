import re
from typing import Dict, List, Tuple

POWER_WORDS = {
    "secret", "viral", "free", "never", "always", "stop", "wait", "mistake",
    "truth", "money", "growth", "hack", "crazy", "insane", "best", "worst",
    "ai", "first", "million", "billion", "important", "warning", "huge",
    "fast", "instant", "proven", "magic", "power", "now", "today", "why", "how",
}

ASPECT_PLAYRES = {
    "9:16": (1080, 1920, 68, 340),
    "1:1": (1080, 1080, 56, 150),
    "16:9": (1920, 1080, 64, 120),
}


class SubtitleService:
    """
    Generates animated word-highlighted ASS subtitles (karaoke / active-word pop)
    with emphasis on important keywords and timeline remapping for silence-cut clips.
    """

    @staticmethod
    def _escape(text: str) -> str:
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        return text.replace("\r\n", " ").replace("\n", " ").strip()

    @staticmethod
    def _is_important(word: str) -> bool:
        clean = re.sub(r"[^A-Za-z0-9%$]", "", word)
        if not clean:
            return False
        if any(ch.isdigit() for ch in clean):
            return True
        if len(clean) >= 3 and clean.isupper():
            return True
        return clean.lower() in POWER_WORDS

    @staticmethod
    def _fmt_time(secs: float) -> str:
        secs = max(0.0, secs)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        cs = int(round((s - int(s)) * 100))
        if cs >= 100:
            cs = 0
            s += 1
        return f"{int(h):01d}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    @staticmethod
    def _remap_timestamp(
        rel_time: float,
        kept_chunks: List[Tuple[float, float]],
        transition_dur: float,
    ) -> float | None:
        """Map a clip-relative timestamp onto the post-silence-cut output timeline."""
        if not kept_chunks:
            return rel_time

        out_cursor = 0.0
        for idx, (c_start, c_end) in enumerate(kept_chunks):
            chunk_len = c_end - c_start
            if c_start <= rel_time <= c_end:
                return max(0.0, out_cursor + (rel_time - c_start))
            out_cursor += chunk_len
            if idx < len(kept_chunks) - 1:
                out_cursor = max(0.0, out_cursor - transition_dur)
        return None

    @classmethod
    def generate_animated_ass(
        cls,
        segments: List[Dict],
        clip_start: float,
        clip_end: float,
        out_path: str,
        aspect_ratio: str = "9:16",
        kept_chunks: List[Tuple[float, float]] | None = None,
        transition_dur: float = 0.0,
    ) -> int:
        """Write an animated word-highlighted ASS file. Returns number of dialogue events written."""
        play_x, play_y, font_size, margin_v = ASPECT_PLAYRES.get(aspect_ratio, ASPECT_PLAYRES["9:16"])

        header = f"""[Script Info]
Title: VIRALCUT AI Animated Subtitles
ScriptType: v4.00+
PlayResX: {play_x}
PlayResY: {play_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,2,70,70,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # Collect words overlapping [clip_start, clip_end]
        clip_words: List[Dict] = []
        for seg in segments or []:
            seg_s = float(seg.get("start", 0.0))
            seg_e = float(seg.get("end", 0.0))
            if seg_e <= clip_start or seg_s >= clip_end:
                continue

            words = seg.get("words") or []
            if words:
                for w in words:
                    ws = float(w.get("start", seg_s))
                    we = float(w.get("end", seg_e))
                    wt = cls._escape(str(w.get("word", "")))
                    if not wt or we <= clip_start or ws >= clip_end:
                        continue
                    clip_words.append(
                        {
                            "start": max(0.0, ws - clip_start),
                            "end": min(clip_end - clip_start, max(we - clip_start, ws - clip_start + 0.08)),
                            "word": wt,
                        }
                    )
            else:
                text = cls._escape(str(seg.get("text", "")))
                tokens = [t for t in text.split() if t]
                if not tokens:
                    continue
                eff_s = max(0.0, seg_s - clip_start)
                eff_e = min(clip_end - clip_start, seg_e - clip_start)
                span = max(0.2, eff_e - eff_s)
                step = span / len(tokens)
                for i, tok in enumerate(tokens):
                    clip_words.append(
                        {
                            "start": eff_s + i * step,
                            "end": eff_s + (i + 1) * step,
                            "word": tok,
                        }
                    )

        # Remap word timings if silence removal altered the timeline
        mapped_words: List[Dict] = []
        for w in clip_words:
            if kept_chunks:
                ns = cls._remap_timestamp(w["start"], kept_chunks, transition_dur)
                ne = cls._remap_timestamp(w["end"], kept_chunks, transition_dur)
                if ns is None and ne is None:
                    continue
                if ns is None:
                    ns = max(0.0, ne - 0.15)
                if ne is None:
                    ne = ns + 0.15
                if ne <= ns:
                    ne = ns + 0.08
                mapped_words.append({"start": ns, "end": ne, "word": w["word"]})
            else:
                mapped_words.append(w)

        # Group into punchy 4-word caption phrases and highlight active word per step
        events: List[str] = []
        phrase_size = 4
        for idx in range(0, len(mapped_words), phrase_size):
            group = mapped_words[idx : idx + phrase_size]
            if not group:
                continue

            for active_i, active_word in enumerate(group):
                ev_s = active_word["start"]
                ev_e = (
                    group[active_i + 1]["start"]
                    if active_i + 1 < len(group)
                    else active_word["end"]
                )
                if ev_e <= ev_s:
                    ev_e = ev_s + 0.12

                styled_tokens = []
                for j, tok in enumerate(group):
                    word_txt = tok["word"]
                    important = cls._is_important(word_txt)
                    if j == active_i:
                        # Active spoken word: vibrant yellow/gold pop (+ cyan for power words)
                        color = "&H0000D7FF&" if important else "&H0000FFFF&"
                        styled_tokens.append(
                            f"{{\\c{color}\\fscx114\\fscy114\\t(0,90,\\fscx106\\fscy106)}}{word_txt}{{\\r}}"
                        )
                    elif important:
                        # Highlighted keyword even when not currently active
                        styled_tokens.append(f"{{\\c&H0080FF00&}}{word_txt}{{\\r}}")
                    else:
                        styled_tokens.append(word_txt)

                line_text = "{\\fad(40,40)}" + " ".join(styled_tokens)
                events.append(
                    f"Dialogue: 0,{cls._fmt_time(ev_s)},{cls._fmt_time(ev_e)},Default,,0,0,0,,{line_text}"
                )

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + ("\n" if events else ""))

        return len(events)
