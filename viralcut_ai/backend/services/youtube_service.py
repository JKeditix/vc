import json
import os
import re
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from backend.config import SUBTITLES_DIR, UPLOADS_DIR
from backend.services.media_service import MediaService


class YouTubeService:
    """Downloads permitted videos & real captions from YouTube URLs using yt-dlp."""

    ALLOWED_HOSTS = (
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "music.youtube.com",
    )

    _PROGRESS_RE = re.compile(r"\[download\]\s+([0-9]+(?:\.[0-9]+)?)%(.*)")

    @classmethod
    def validate_url(cls, url: str) -> str:
        clean = (url or "").strip()
        parsed = urlparse(clean)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Please provide a valid HTTP/HTTPS video URL.")
        host = parsed.netloc.lower().split(":")[0]
        if not any(host == h or host.endswith("." + h) for h in cls.ALLOWED_HOSTS):
            raise ValueError(
                "Please enter a valid YouTube URL (youtube.com or youtu.be)."
            )
        return clean

    @classmethod
    def fetch_metadata(cls, clean_url: str) -> Dict:
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--skip-download",
            "-J",
            clean_url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if res.returncode == 0 and (res.stdout or "").strip():
            try:
                meta = json.loads(res.stdout)
                return {
                    "title": (meta.get("title") or "YouTube Video").strip()[:250],
                    "duration": float(meta.get("duration") or 0.0),
                }
            except json.JSONDecodeError:
                pass
        return {"title": "YouTube Video", "duration": 0.0}

    @classmethod
    def fetch_captions(cls, url: str, output_id: str) -> Optional[Dict]:
        """Fetch real YouTube manual or auto-generated json3 captions in 1-2 seconds when available."""
        clean_url = cls.validate_url(url)
        os.makedirs(SUBTITLES_DIR, exist_ok=True)
        out_tmpl = os.path.join(SUBTITLES_DIR, f"ytcap_{output_id}.%(ext)s")

        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--skip-download",
            "--write-sub",
            "--write-auto-sub",
            "--sub-langs",
            "en.*,en,hi.*,hi",
            "--sub-format",
            "json3",
            "-o",
            out_tmpl,
            clean_url,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception:
            return None

        cap_file = None
        for fname in os.listdir(SUBTITLES_DIR):
            if fname.startswith(f"ytcap_{output_id}.") and fname.endswith(".json3"):
                cap_file = os.path.join(SUBTITLES_DIR, fname)
                break

        if not cap_file or not os.path.exists(cap_file):
            return None

        try:
            with open(cap_file, "r", encoding="utf-8") as f:
                raw = json.load(f)

            segments: List[Dict] = []
            full_parts: List[str] = []
            for ev in raw.get("events", []):
                segs = ev.get("segs")
                if not segs:
                    continue
                t_start = float(ev.get("tStartMs", 0)) / 1000.0
                d_dur = float(ev.get("dDurationMs", 2500)) / 1000.0
                t_end = t_start + max(0.3, d_dur)

                words = []
                text_tokens = []
                for s in segs:
                    tok = str(s.get("utf8", "")).replace("\n", " ").strip()
                    if not tok:
                        continue
                    offset = float(s.get("tOffsetMs", 0)) / 1000.0
                    w_start = t_start + offset
                    text_tokens.append(tok)
                    for subtok in tok.split():
                        words.append({"start": round(w_start, 3), "end": round(w_start + 0.25, 3), "word": subtok})

                line_text = " ".join(text_tokens).strip()
                if line_text:
                    # Fix word end times smoothly
                    for idx, w in enumerate(words):
                        w["end"] = words[idx + 1]["start"] if idx + 1 < len(words) else round(t_end, 3)
                        if w["end"] <= w["start"]:
                            w["end"] = round(w["start"] + 0.15, 3)

                    full_parts.append(line_text)
                    segments.append(
                        {
                            "start": round(t_start, 3),
                            "end": round(t_end, 3),
                            "text": line_text,
                            "words": words,
                        }
                    )

            if not segments:
                return None

            return {
                "engine": "youtube-captions (json3)",
                "language": "auto",
                "text": " ".join(full_parts),
                "segments": segments,
                "note": "Instant timestamped captions fetched directly from YouTube.",
            }
        except Exception:
            return None
        finally:
            try:
                os.remove(cap_file)
            except OSError:
                pass

    @classmethod
    def download_video(
        cls,
        url: str,
        output_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        metadata_callback: Optional[Callable[[Dict], None]] = None,
    ) -> Dict:
        clean_url = cls.validate_url(url)
        MediaService.ensure_ffmpeg()
        os.makedirs(UPLOADS_DIR, exist_ok=True)

        if progress_callback:
            progress_callback(0.02, "Fetching YouTube video info...")

        meta = cls.fetch_metadata(clean_url)
        title = meta["title"]
        est_duration = meta["duration"]
        if metadata_callback:
            metadata_callback(meta)

        max_height = 720 if est_duration >= 2700 else 1080
        fmt_selector = (
            f"bestvideo[height<={max_height}][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={max_height}][ext=mp4]/"
            f"best[height<={max_height}]/best"
        )

        out_template = os.path.join(UPLOADS_DIR, f"{output_id}.%(ext)s")
        yt_cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--newline",
            "--progress",
            "--concurrent-fragments",
            "8",
            "-f",
            fmt_selector,
            "--merge-output-format",
            "mp4",
            "-o",
            out_template,
            clean_url,
        ]

        if progress_callback:
            progress_callback(0.05, f"Downloading ({max_height}p MP4): {title[:60]}...")

        proc = subprocess.Popen(
            yt_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        tail_lines = []
        last_update = 0.0
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            tail_lines.append(line)
            if len(tail_lines) > 25:
                tail_lines.pop(0)

            now = time.monotonic()
            if progress_callback and (now - last_update >= 1.0):
                m = cls._PROGRESS_RE.search(line)
                if m:
                    pct = float(m.group(1))
                    extra = m.group(2).strip()
                    progress_callback(
                        min(0.92, 0.05 + (pct / 100.0) * 0.87),
                        f"Downloading video ({max_height}p): {pct:.1f}% {extra[:45]}".strip(),
                    )
                    last_update = now
                elif "[Merger]" in line or "Merging formats" in line:
                    progress_callback(0.95, "Merging video and audio tracks...")
                    last_update = now

        returncode = proc.wait()
        if returncode != 0:
            err_detail = "\n".join(tail_lines[-8:]) or "Unknown yt-dlp error"
            raise RuntimeError(f"YouTube download failed: {err_detail[-500:]}")

        preferred = os.path.join(UPLOADS_DIR, f"{output_id}.mp4")
        file_path = preferred if os.path.exists(preferred) else ""
        if not file_path:
            for fname in os.listdir(UPLOADS_DIR):
                if fname.startswith(f"{output_id}.") and not fname.endswith((".part", ".ytdl", ".temp.mp4")):
                    file_path = os.path.join(UPLOADS_DIR, fname)
                    break

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded video file could not be located on disk.")

        if progress_callback:
            progress_callback(1.0, "Download complete. Inspecting video streams...")

        info = MediaService.probe_video(file_path)
        return {
            "file_path": file_path,
            "title": title,
            **info,
        }
