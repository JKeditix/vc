import json
import os
import re
import shutil
import subprocess
from typing import Dict, List, Tuple

from backend.config import AUDIO_DIR, UPLOADS_DIR, settings


def sanitize_filename(name: str, fallback: str = "video") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "").strip("._")
    return cleaned[:100] or fallback


class MediaService:
    """Handles upload validation, ffprobe inspection, audio extraction, and silence detection."""

    @staticmethod
    def ensure_ffmpeg() -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError(
                "FFmpeg and ffprobe are required and must be available on your system PATH."
            )

    @staticmethod
    def validate_extension(filename: str) -> str:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
            raise ValueError(f"Unsupported video format '{ext or 'unknown'}'. Allowed: {allowed}")
        return ext

    @staticmethod
    def save_uploaded_file(file_obj, original_filename: str, file_id: str) -> str:
        ext = MediaService.validate_extension(original_filename)
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        dest_path = os.path.join(UPLOADS_DIR, f"{file_id}{ext}")

        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        written = 0
        chunk_size = 1024 * 1024

        try:
            with open(dest_path, "wb") as out:
                while True:
                    chunk = file_obj.read(chunk_size)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise ValueError(f"File exceeds maximum size limit of {settings.MAX_UPLOAD_MB} MB.")
                    out.write(chunk)

            if written == 0:
                raise ValueError("Uploaded file is empty.")
        except Exception:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise

        return dest_path

    @staticmethod
    def probe_video(file_path: str) -> Dict:
        MediaService.ensure_ffmpeg()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"ffprobe failed to inspect video: {res.stderr.strip()}")

        data = json.loads(res.stdout or "{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            raise ValueError("The uploaded file does not contain a valid video stream.")

        duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)

        fps = 30.0
        rate_str = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "30/1"
        if "/" in rate_str:
            num_s, den_s = rate_str.split("/", 1)
            try:
                num, den = float(num_s), float(den_s)
                if den > 0 and num > 0:
                    fps = round(num / den, 3)
            except ValueError:
                pass

        return {
            "duration": round(duration, 3),
            "width": width,
            "height": height,
            "fps": fps,
            "has_audio": audio_stream is not None,
            "video_codec": video_stream.get("codec_name", ""),
            "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
        }

    @staticmethod
    def extract_audio(video_path: str, output_id: str) -> str:
        MediaService.ensure_ffmpeg()
        os.makedirs(AUDIO_DIR, exist_ok=True)
        out_path = os.path.join(AUDIO_DIR, f"{output_id}.wav")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            out_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Audio extraction failed: {res.stderr.strip()}")
        return out_path

    @staticmethod
    def detect_silences(
        media_path: str,
        start_time: float = 0.0,
        duration: float | None = None,
        noise_db: float = -32.0,
        min_silence_duration: float = 0.45,
    ) -> List[Tuple[float, float]]:
        """Detect silent intervals relative to the analyzed range using FFmpeg silencedetect."""
        MediaService.ensure_ffmpeg()
        cmd = ["ffmpeg", "-hide_banner", "-nostats"]
        if start_time > 0:
            cmd += ["-ss", str(start_time)]
        if duration is not None and duration > 0:
            cmd += ["-t", str(duration)]
        cmd += [
            "-i",
            media_path,
            "-vn",
            "-af",
            f"silencedetect=noise={noise_db}dB:d={min_silence_duration}",
            "-f",
            "null",
            "-",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        stderr = res.stderr or ""

        silences: List[Tuple[float, float]] = []
        current_start: float | None = None

        start_re = re.compile(r"silence_start:\s*([0-9.]+)")
        end_re = re.compile(r"silence_end:\s*([0-9.]+)")

        for line in stderr.splitlines():
            m_start = start_re.search(line)
            if m_start:
                current_start = float(m_start.group(1))
                continue
            m_end = end_re.search(line)
            if m_end and current_start is not None:
                end_val = float(m_end.group(1))
                if end_val > current_start:
                    silences.append((round(current_start, 3), round(end_val, 3)))
                current_start = None

        if current_start is not None and duration is not None and duration > current_start:
            silences.append((round(current_start, 3), round(duration, 3)))

        return silences

    @staticmethod
    def compute_active_segments(
        total_duration: float,
        silences: List[Tuple[float, float]],
        min_segment: float = 0.35,
        padding: float = 0.12,
    ) -> List[Tuple[float, float]]:
        """Invert silent intervals into active non-silent speech/audio intervals."""
        if total_duration <= 0:
            return []
        if not silences:
            return [(0.0, round(total_duration, 3))]

        raw: List[Tuple[float, float]] = []
        cursor = 0.0
        for s_start, s_end in sorted(silences):
            keep_end = min(total_duration, s_start + padding)
            if keep_end - cursor >= min_segment:
                raw.append((max(0.0, cursor), keep_end))
            cursor = max(0.0, s_end - padding)

        if total_duration - cursor >= min_segment:
            raw.append((cursor, total_duration))

        if not raw:
            return [(0.0, round(total_duration, 3))]

        # Merge overlapping or nearly touching active windows
        merged: List[Tuple[float, float]] = []
        for start, end in raw:
            if merged and start <= merged[-1][1] + 0.15:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((round(start, 3), round(end, 3)))
        return merged
