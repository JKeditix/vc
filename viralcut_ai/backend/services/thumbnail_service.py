import os
import subprocess
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from backend.config import THUMBNAILS_DIR
from backend.services.media_service import MediaService


class ThumbnailService:
    """
    Extracts a real keyframe from a rendered short clip using FFmpeg and
    enhances it with Pillow (subtle color punch + clean headline banner)
    to generate ready-to-use thumbnail previews.
    """

    @staticmethod
    def _load_font(size: int):
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    @classmethod
    def generate_thumbnail(
        cls,
        video_path: str,
        clip_id: str,
        headline: str = "",
        category: str = "Highlight",
        virality_score: int = 85,
        timestamp_ratio: float = 0.2,
    ) -> Optional[str]:
        if not video_path or not os.path.exists(video_path):
            return None

        MediaService.ensure_ffmpeg()
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)

        info = MediaService.probe_video(video_path)
        dur = max(0.5, float(info.get("duration") or 1.0))
        seek_t = round(min(dur * timestamp_ratio, max(0.0, dur - 0.2)), 2)

        raw_frame = os.path.join(THUMBNAILS_DIR, f"raw_{clip_id}.jpg")
        out_path = os.path.join(THUMBNAILS_DIR, f"thumb_{clip_id}.jpg")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(seek_t),
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            raw_frame,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(raw_frame):
            return None

        try:
            with Image.open(raw_frame) as im:
                img = im.convert("RGB")
                # Resize preview cleanly while preserving aspect ratio
                img.thumbnail((720, 1280), Image.Resampling.LANCZOS)
                img = ImageEnhance.Contrast(img).enhance(1.08)
                img = ImageEnhance.Color(img).enhance(1.10)

                w, h = img.size
                overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)

                # Bottom dark band for crisp headline readability
                band_h = max(90, int(h * 0.20))
                draw.rectangle([(0, h - band_h), (w, h)], fill=(9, 13, 22, 200))

                # Top badge pill
                badge_font = cls._load_font(max(18, int(w * 0.042)))
                badge_text = f"{category.upper()}  |  {virality_score}/100"
                draw.rounded_rectangle([(18, 18), (min(w - 18, 290), 58)], radius=12, fill=(79, 70, 229, 230))
                draw.text((32, 26), badge_text, fill=(255, 255, 255, 255), font=badge_font)

                # Headline text inside bottom band
                short_title = " ".join((headline or "VIRAL SHORT").split()[:6]).upper()
                title_font = cls._load_font(max(22, int(w * 0.056)))
                draw.text((24, h - band_h + 24), short_title[:36], fill=(250, 204, 21, 255), font=title_font)

                combined = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                combined.save(out_path, format="JPEG", quality=88, optimize=True)
        finally:
            if os.path.exists(raw_frame):
                os.remove(raw_frame)

        return out_path if os.path.exists(out_path) else None
