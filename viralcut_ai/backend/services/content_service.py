import re
from typing import Dict, List

CATEGORY_HASHTAGS = {
    "Hook": ["#Shorts", "#Reels", "#TikTok", "#ViralHook", "#MustWatch"],
    "Funny": ["#Shorts", "#Reels", "#FunnyClips", "#Comedy", "#Relatable"],
    "Emotional": ["#Shorts", "#Reels", "#Storytime", "#RealTalk", "#Inspiration"],
    "Educational": ["#Shorts", "#Reels", "#LearnOnTikTok", "#TipsAndTricks", "#Growth"],
    "Highlight": ["#Shorts", "#Reels", "#TikTok", "#Highlights", "#ViralCutAI"],
}

CATEGORY_THUMB_PROMPTS = {
    "Hook": "Close-up expressive speaker frame + bold 3-word yellow hook banner at top",
    "Funny": "Peak reaction frame with expressive facial cue + high-contrast white/red punchline text",
    "Emotional": "Warm close-up frame with dark bottom vignette + minimal bold emotional quote",
    "Educational": "Clean mid-shot frame with clear 3-word takeaway badge and high-contrast arrow",
    "Highlight": "High-contrast keyframe at peak energy moment + bold centered title overlay",
}

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "your", "have", "what", "when",
    "where", "about", "there", "their", "would", "could", "should", "into", "just",
    "like", "they", "them", "then", "than", "been", "were", "will", "here", "make",
    "more", "very", "also", "some", "only", "most", "even", "much", "such", "each",
}


class ContentService:
    """
    Ensures every detected clip has complete AI-generated copywriting:
      - Attractive title
      - Description
      - Hashtags
      - Opening hook
      - Thumbnail suggestion
    Preserves Gemini-generated values when present and fills any missing fields
    using grounded extraction from the clip's transcript & category.
    """

    @classmethod
    def enrich_clip_content(cls, clip_data: Dict, project_title: str = "") -> Dict:
        title = (clip_data.get("title") or "Viral Highlight").strip()
        summary = (clip_data.get("summary") or "").strip()
        category = (clip_data.get("category") or "Highlight").strip()
        score = int(clip_data.get("virality_score") or 80)

        keywords = cls._extract_keywords(f"{title} {summary} {project_title}")

        ai_title = (clip_data.get("ai_title") or "").strip()
        if not ai_title:
            ai_title = cls._build_title(title, category)

        ai_hook = (clip_data.get("ai_hook") or "").strip()
        if not ai_hook:
            ai_hook = cls._build_hook(summary, title, category)

        ai_description = (clip_data.get("ai_description") or "").strip()
        if not ai_description:
            lead = summary if summary else f"Key {category.lower()} moment from {project_title or 'this video'}."
            ai_description = (
                f"{lead}\n\n"
                "Watch until the end and drop your thoughts in the comments!"
            )

        ai_hashtags = (clip_data.get("ai_hashtags") or "").strip()
        if not ai_hashtags:
            base_tags = list(CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["Highlight"]))
            for kw in keywords[:3]:
                tag = "#" + kw.capitalize()
                if tag not in base_tags:
                    base_tags.append(tag)
            ai_hashtags = " ".join(base_tags[:7])

        thumb_suggestion = (clip_data.get("thumbnail_suggestion") or "").strip()
        if not thumb_suggestion:
            key_phrase = " ".join(title.split()[:4]).upper()
            base_idea = CATEGORY_THUMB_PROMPTS.get(category, CATEGORY_THUMB_PROMPTS["Highlight"])
            thumb_suggestion = f"{base_idea} — Text: \"{key_phrase}\" (Score {score}/100)"

        enriched = dict(clip_data)
        enriched["ai_title"] = ai_title[:250]
        enriched["ai_hook"] = ai_hook[:250]
        enriched["ai_description"] = ai_description
        enriched["ai_hashtags"] = ai_hashtags
        enriched["thumbnail_suggestion"] = thumb_suggestion
        return enriched

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", text or "")
        seen = set()
        out: List[str] = []
        for w in words:
            lw = w.lower()
            if lw in STOPWORDS or lw in seen:
                continue
            seen.add(lw)
            out.append(lw)
        return out

    @staticmethod
    def _build_title(title: str, category: str) -> str:
        clean = title.rstrip(".!")
        if len(clean) >= 12:
            return clean
        prefix = {
            "Hook": "Wait For This:",
            "Funny": "You Won't Believe This Moment:",
            "Emotional": "The Real Story Behind",
            "Educational": "How This Actually Works:",
        }.get(category, "Top Highlight:")
        return f"{prefix} {clean}"

    @staticmethod
    def _build_hook(summary: str, title: str, category: str) -> str:
        if summary:
            first_clause = re.split(r"[.!?]+", summary)[0].strip()
            if len(first_clause) >= 10:
                return first_clause[:140]
        defaults = {
            "Hook": "Stop scrolling — watch the next 5 seconds carefully.",
            "Funny": "Wait until you see what happens right here...",
            "Emotional": "This is the moment that changes everything.",
            "Educational": "Save this before you make the same mistake.",
        }
        return defaults.get(category, title[:140])
