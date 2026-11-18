import json
import math
import re
from typing import Dict, List, Tuple

from backend.config import settings

HOOK_PATTERNS = re.compile(
    r"\b(stop|wait|secret|never|always|why|how to|mistake|truth|nobody|actually|listen|crazy|insane|imagine|here is|the reason)\b|\?",
    re.IGNORECASE,
)
FUNNY_PATTERNS = re.compile(
    r"\b(haha|laugh|funny|hilarious|ridiculous|awkward|fail|bro|dude|wtf|wild|joke|prank|oops)\b",
    re.IGNORECASE,
)
EMOTIONAL_PATTERNS = re.compile(
    r"\b(love|cry|tears|heart|fear|lost|dream|hope|proud|pain|struggle|changed my life|grateful|honest|vulnerable)\b|!",
    re.IGNORECASE,
)
EDUCATIONAL_PATTERNS = re.compile(
    r"\b(step|tip|framework|strategy|method|rule|formula|percent|%|example|learn|guide|first|second|third|data|study|result)\b",
    re.IGNORECASE,
)


class AnalyzerService:
    """
    Detects high-potential viral clips with exact timestamps, categories
    (Hook, Funny, Emotional, Educational, Highlight), and viral potential scores.
    Uses Gemini when GEMINI_API_KEY is configured, with a real text/signal scoring fallback.
    """

    @classmethod
    def detect_clips(
        cls,
        transcript_data: Dict,
        total_duration: float,
        target_clip_duration: int = 30,
        max_clips: int = 6,
    ) -> List[Dict]:
        safe_duration = max(float(total_duration or 0.0), 1.0)
        desired_count = max(1, min(int(max_clips or 6), 10))
        target_dur = max(10, min(int(target_clip_duration or 30), 90))

        segments = transcript_data.get("segments") or []
        has_text = any((s.get("text") or "").strip() for s in segments)

        if (settings.GEMINI_API_KEY or "").strip() and has_text:
            try:
                gemini_clips = cls._analyze_with_gemini(
                    segments=segments,
                    total_duration=safe_duration,
                    target_dur=target_dur,
                    max_clips=desired_count,
                )
                normalized = cls._normalize_clips(gemini_clips, safe_duration)
                if normalized:
                    return normalized[:desired_count]
            except Exception as err:
                print(f"[AnalyzerService] Gemini analysis fallback: {err}")

        signal_clips = cls._analyze_by_signals(
            segments=segments,
            total_duration=safe_duration,
            target_dur=target_dur,
            max_clips=desired_count,
        )
        return cls._normalize_clips(signal_clips, safe_duration)[:desired_count]

    @classmethod
    def _analyze_with_gemini(
        cls,
        segments: List[Dict],
        total_duration: float,
        target_dur: int,
        max_clips: int,
    ) -> List[Dict]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
        compact_segments = [
            {"start": s["start"], "end": s["end"], "text": s.get("text", "")}
            for s in segments
            if (s.get("text") or "").strip()
        ]

        prompt = f"""
You are a viral short-form video producer for YouTube Shorts, Instagram Reels, and TikTok.
Analyze the COMPLETE transcript below (total video duration: {round(total_duration, 2)} seconds).

Select up to {max_clips} of the strongest, non-overlapping viral moments (5-10 clips for long videos when suitable).
Prefer clip lengths close to {target_dur} seconds (allowed range: 10 to 90 seconds, strictly within 0 to {round(total_duration, 2)}s).

For each clip, classify its primary category as one of:
"Hook", "Funny", "Emotional", "Educational", or "Highlight".

Return ONLY a valid JSON array with this exact schema:
[
  {{
    "title": "Concise descriptive clip title",
    "summary": "1-2 sentence summary grounded in what is actually said",
    "start_time": 12.5,
    "end_time": 42.5,
    "virality_score": 92,
    "virality_reason": "Strong pattern-interrupt hook and high-value takeaway",
    "category": "Hook",
    "ai_title": "Scroll-stopping short title",
    "ai_description": "Engaging caption with call to action",
    "ai_hashtags": "#shorts #reels #viral",
    "ai_hook": "Punchy 3-second opening hook line",
    "thumbnail_suggestion": "Frame description + bold 3-word text overlay idea"
  }}
]

Transcript:
{json.dumps(compact_segments, ensure_ascii=False)}
"""
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()

        parsed = json.loads(raw)
        if isinstance(parsed, dict) and isinstance(parsed.get("clips"), list):
            return parsed["clips"]
        if isinstance(parsed, list):
            return parsed
        return []

    @classmethod
    def _analyze_by_signals(
        cls,
        segments: List[Dict],
        total_duration: float,
        target_dur: int,
        max_clips: int,
    ) -> List[Dict]:
        # Short video: return full video as a single clip if shorter than target window
        if total_duration <= max(target_dur, 15):
            full_text = " ".join((s.get("text") or "").strip() for s in segments).strip()
            category, score, reason = cls._score_text_window(full_text, total_duration, len(segments))
            return [
                {
                    "title": cls._derive_title(full_text, category, 1),
                    "summary": full_text[:240] if full_text else f"Full highlight segment (0.0s - {round(total_duration, 1)}s).",
                    "start_time": 0.0,
                    "end_time": round(total_duration, 2),
                    "virality_score": score,
                    "virality_reason": reason,
                    "category": category,
                }
            ]

        # Build candidate windows anchored on real transcript/audio segments
        candidates: List[Dict] = []
        effective_win = min(float(target_dur), total_duration)

        if segments:
            for idx, seg in enumerate(segments):
                win_start = float(seg["start"])
                if win_start >= total_duration - 3.0:
                    break
                win_end = min(total_duration, win_start + effective_win)

                # Snap end cleanly to a segment boundary near target duration
                collected = []
                for j in range(idx, len(segments)):
                    s_j = segments[j]
                    if float(s_j["start"]) >= win_end + 4.0:
                        break
                    collected.append(s_j)
                    if float(s_j["end"]) >= win_end - 2.0:
                        win_end = min(total_duration, float(s_j["end"]))
                        break

                if win_end - win_start < min(6.0, total_duration * 0.4):
                    win_end = min(total_duration, win_start + effective_win)

                win_text = " ".join((s.get("text") or "").strip() for s in collected).strip()
                active_time = sum(max(0.0, float(s["end"]) - float(s["start"])) for s in collected)
                density = active_time / max(1.0, win_end - win_start)

                category, score, reason = cls._score_text_window(
                    win_text,
                    win_end - win_start,
                    len(collected),
                    active_ratio=density,
                    is_opening=(win_start < 10.0),
                )
                candidates.append(
                    {
                        "start_time": round(win_start, 2),
                        "end_time": round(win_end, 2),
                        "text": win_text,
                        "category": category,
                        "virality_score": score,
                        "virality_reason": reason,
                    }
                )
        else:
            # No audio/segments: evenly spaced visual windows across the real video duration
            count = min(max_clips, max(1, int(math.floor(total_duration / max(effective_win, 5.0)))))
            step = total_duration / count
            for i in range(count):
                s_t = round(i * step, 2)
                e_t = round(min(total_duration, s_t + effective_win), 2)
                if e_t - s_t < 2.0:
                    continue
                candidates.append(
                    {
                        "start_time": s_t,
                        "end_time": e_t,
                        "text": "",
                        "category": "Hook" if i == 0 else "Highlight",
                        "virality_score": max(65, 84 - i * 3),
                        "virality_reason": "Evenly sampled scene window across source video.",
                    }
                )

        # Greedy non-overlapping selection ranked by viral potential score
        candidates.sort(key=lambda c: (-c["virality_score"], c["start_time"]))
        selected: List[Dict] = []

        for cand in candidates:
            if len(selected) >= max_clips:
                break
            overlaps = any(
                min(cand["end_time"], s["end_time"]) - max(cand["start_time"], s["start_time"]) > 2.0
                for s in selected
            )
            if not overlaps:
                selected.append(cand)

        selected.sort(key=lambda c: -c["virality_score"])

        results = []
        for idx, item in enumerate(selected, start=1):
            text = item["text"]
            cat = item["category"]
            results.append(
                {
                    "title": cls._derive_title(text, cat, idx),
                    "summary": (
                        text[:240]
                        if text
                        else f"Active segment from {item['start_time']}s to {item['end_time']}s."
                    ),
                    "start_time": item["start_time"],
                    "end_time": item["end_time"],
                    "virality_score": item["virality_score"],
                    "virality_reason": item["virality_reason"],
                    "category": cat,
                }
            )
        return results

    @staticmethod
    def _score_text_window(
        text: str,
        duration: float,
        segment_count: int,
        active_ratio: float = 0.7,
        is_opening: bool = False,
    ) -> Tuple[str, int, str]:
        hook_hits = len(HOOK_PATTERNS.findall(text))
        funny_hits = len(FUNNY_PATTERNS.findall(text))
        emotional_hits = len(EMOTIONAL_PATTERNS.findall(text))
        edu_hits = len(EDUCATIONAL_PATTERNS.findall(text))

        cat_scores = {
            "Hook": hook_hits * 2 + (1 if is_opening else 0),
            "Educational": edu_hits * 2,
            "Emotional": emotional_hits * 2,
            "Funny": funny_hits * 2,
        }
        best_cat, best_val = max(cat_scores.items(), key=lambda kv: kv[1])
        category = best_cat if best_val > 0 else ("Hook" if is_opening else "Highlight")

        word_count = len(text.split())
        wps = word_count / max(1.0, duration)

        score = 62
        reasons = []
        if hook_hits:
            score += min(14, hook_hits * 5)
            reasons.append("strong hook phrasing")
        if edu_hits:
            score += min(10, edu_hits * 4)
            reasons.append("actionable insight")
        if emotional_hits:
            score += min(10, emotional_hits * 4)
            reasons.append("high emotional energy")
        if funny_hits:
            score += min(10, funny_hits * 5)
            reasons.append("entertaining reaction")
        if 1.8 <= wps <= 3.8:
            score += 8
            reasons.append("engaging speaking pace")
        if active_ratio >= 0.65:
            score += 6
            reasons.append("dense active audio")
        if segment_count >= 2:
            score += 4

        score = max(55, min(98, int(score)))
        reason_str = (
            "Detected " + ", ".join(reasons) + "."
            if reasons
            else f"Sustained audio/visual activity ({round(active_ratio * 100)}% active)."
        )
        return category, score, reason_str

    @staticmethod
    def _derive_title(text: str, category: str, index: int) -> str:
        if text:
            first_sentence = re.split(r"[.!?]+", text)[0].strip()
            words = first_sentence.split()
            if len(words) >= 3:
                snippet = " ".join(words[:8])
                return snippet[:70]
        return f"{category} Moment #{index}"

    @staticmethod
    def _normalize_clips(raw_clips: List[Dict], total_duration: float) -> List[Dict]:
        allowed_cats = {"Hook", "Funny", "Emotional", "Educational", "Highlight"}
        normalized = []
        for idx, item in enumerate(raw_clips, start=1):
            if not isinstance(item, dict):
                continue
            start = max(0.0, min(float(item.get("start_time", 0.0)), max(0.0, total_duration - 1.0)))
            end = float(item.get("end_time", start + 15.0))
            end = max(start + 1.0, min(end, total_duration))
            if end <= start:
                continue

            cat = str(item.get("category") or "Highlight").strip().title()
            if cat not in allowed_cats:
                cat = "Highlight"

            score = int(item.get("virality_score", 80))
            score = max(1, min(100, score))

            normalized.append(
                {
                    "title": str(item.get("title") or f"Viral Clip #{idx}").strip()[:250],
                    "summary": str(item.get("summary") or "").strip(),
                    "start_time": round(start, 2),
                    "end_time": round(end, 2),
                    "duration": round(end - start, 2),
                    "virality_score": score,
                    "virality_reason": str(item.get("virality_reason") or "").strip(),
                    "category": cat,
                    "ai_title": str(item.get("ai_title") or "").strip(),
                    "ai_description": str(item.get("ai_description") or "").strip(),
                    "ai_hashtags": str(item.get("ai_hashtags") or "").strip(),
                    "ai_hook": str(item.get("ai_hook") or "").strip(),
                    "thumbnail_suggestion": str(item.get("thumbnail_suggestion") or "").strip(),
                }
            )
        return normalized
