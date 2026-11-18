import json
import os
import re
import time
import wave
from typing import Callable, Dict, List, Optional

import numpy as np

from backend.config import settings
from backend.services.media_service import MediaService
from backend.services.youtube_service import YouTubeService


class TranscriptionService:
    """
    Fast, real speech-to-text transcription engine.
    Priority:
      1. Instant YouTube json3 captions when source is a YouTube URL (1-2s even for 2-hour videos)
      2. Local faster-whisper with word-level timestamps (loads 16kHz PCM WAV via wave+numpy, bypassing PyAV incompatibilities)
      3. Gemini multimodal audio transcription (if GEMINI_API_KEY is configured)
      4. Real FFmpeg silence/speech-activity segmentation (never fabricates fake dialogue)
    """

    _whisper_model_cache = {}

    @classmethod
    def _get_whisper_model(cls):
        from faster_whisper import WhisperModel

        key = (settings.WHISPER_MODEL, settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)
        if key not in cls._whisper_model_cache:
            cls._whisper_model_cache[key] = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                cpu_threads=max(2, os.cpu_count() or 4),
            )
        return cls._whisper_model_cache[key]

    @staticmethod
    def _load_wav_float32(audio_path: str) -> np.ndarray:
        """Read 16kHz mono 16-bit PCM WAV directly into float32 numpy array (no PyAV dependency)."""
        with wave.open(audio_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            pcm = np.frombuffer(frames, dtype=np.int16)
            return pcm.astype(np.float32) / 32768.0

    @classmethod
    def transcribe(
        cls,
        video_path: str,
        audio_path: Optional[str],
        duration: float,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        source_url: Optional[str] = None,
        project_id: str = "tmp",
    ) -> Dict:
        # 1. Fast path for YouTube URLs: fetch real YouTube captions in 1-2s
        if source_url:
            if progress_callback:
                progress_callback(0.1, "Checking for YouTube timestamped captions...")
            yt_caps = YouTubeService.fetch_captions(source_url, project_id)
            if yt_caps and yt_caps.get("segments"):
                if progress_callback:
                    progress_callback(1.0, f"Loaded {len(yt_caps['segments'])} caption segments from YouTube.")
                return yt_caps

        if audio_path and os.path.exists(audio_path):
            # 2. Local faster-whisper using direct numpy waveform
            try:
                return cls._transcribe_faster_whisper(audio_path, duration, progress_callback)
            except Exception as whisper_err:
                print(f"[TranscriptionService] faster-whisper unavailable: {whisper_err}")

            # 3. Gemini multimodal audio transcription
            if (settings.GEMINI_API_KEY or "").strip():
                try:
                    return cls._transcribe_gemini_audio(audio_path, duration)
                except Exception as gemini_err:
                    print(f"[TranscriptionService] Gemini audio transcription failed: {gemini_err}")

            # 4. Real FFmpeg speech-activity intervals (never fabricates fake dialogue)
            return cls._segment_audio_activity(audio_path, duration)

        return {
            "engine": "no_audio",
            "language": "unknown",
            "text": "",
            "segments": [],
            "note": "Video has no audio stream; clip detection will use visual/time windows.",
        }

    @classmethod
    def _transcribe_faster_whisper(
        cls,
        audio_path: str,
        duration: float,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict:
        if progress_callback:
            progress_callback(0.05, f"Loading faster-whisper ({settings.WHISPER_MODEL})...")

        audio_np = cls._load_wav_float32(audio_path)
        model = cls._get_whisper_model()
        segments_iter, info = model.transcribe(
            audio_np,
            word_timestamps=True,
            vad_filter=True,
            beam_size=1,
            condition_on_previous_text=False,
        )
        segments: List[Dict] = []
        full_text_parts: List[str] = []
        total_dur = max(1.0, float(duration or getattr(info, "duration", 1.0) or 1.0))
        last_update = 0.0

        for seg in segments_iter:
            text = (seg.text or "").strip()
            words = []
            if getattr(seg, "words", None):
                for w in seg.words:
                    w_text = (w.word or "").strip()
                    if w_text:
                        words.append(
                            {
                                "start": round(float(w.start), 3),
                                "end": round(float(w.end), 3),
                                "word": w_text,
                            }
                        )
            if text:
                full_text_parts.append(text)
                segments.append(
                    {
                        "start": round(float(seg.start), 3),
                        "end": round(float(seg.end), 3),
                        "text": text,
                        "words": words,
                    }
                )

            now = time.monotonic()
            if progress_callback and (now - last_update >= 1.5):
                ratio = min(0.98, float(seg.end) / total_dur)
                mins_done, secs_done = divmod(int(seg.end), 60)
                mins_tot, secs_tot = divmod(int(total_dur), 60)
                progress_callback(
                    ratio,
                    f"Transcribing speech ({mins_done:02d}:{secs_done:02d} / {mins_tot:02d}:{secs_tot:02d})...",
                )
                last_update = now

        return {
            "engine": f"faster-whisper ({settings.WHISPER_MODEL})",
            "language": getattr(info, "language", "en") or "en",
            "text": " ".join(full_text_parts).strip(),
            "segments": segments,
            "note": "Transcribed locally with faster-whisper word-level timestamps.",
        }

    @classmethod
    def _transcribe_gemini_audio(cls, audio_path: str, duration: float) -> Dict:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        prompt = (
            "Transcribe this audio accurately with timestamps. Return ONLY valid JSON matching:\n"
            '{"language": "en", "segments": [{"start": 0.0, "end": 4.5, "text": "..."}]}\n'
            f"Total audio duration is approximately {round(duration, 2)} seconds. "
            "Do not invent words that are not spoken. If there is no speech, return an empty segments array."
        )

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                prompt,
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()

        parsed = json.loads(raw)
        segments: List[Dict] = []
        for s in parsed.get("segments", []):
            start = max(0.0, float(s.get("start", 0.0)))
            end = min(duration, float(s.get("end", start + 1.0)))
            text = str(s.get("text", "")).strip()
            if text and end > start:
                words = cls._estimate_word_timings(text, start, end)
                segments.append(
                    {
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "text": text,
                        "words": words,
                    }
                )

        return {
            "engine": f"gemini-audio ({settings.GEMINI_MODEL})",
            "language": str(parsed.get("language", "en")),
            "text": " ".join(s["text"] for s in segments),
            "segments": segments,
            "note": "Transcribed via Gemini multimodal audio API.",
        }

    @staticmethod
    def _estimate_word_timings(text: str, start: float, end: float) -> List[Dict]:
        tokens = [t for t in text.split() if t]
        if not tokens:
            return []
        span = max(0.1, end - start)
        step = span / len(tokens)
        words = []
        for idx, tok in enumerate(tokens):
            w_start = start + idx * step
            w_end = start + (idx + 1) * step
            words.append(
                {
                    "start": round(w_start, 3),
                    "end": round(w_end, 3),
                    "word": tok,
                }
            )
        return words

    @staticmethod
    def _segment_audio_activity(audio_path: str, duration: float) -> Dict:
        silences = MediaService.detect_silences(audio_path, duration=duration)
        active = MediaService.compute_active_segments(duration, silences)
        segments = [
            {"start": s, "end": e, "text": "", "words": []}
            for s, e in active
            if e - s >= 0.35
        ]
        return {
            "engine": "audio_activity",
            "language": "unknown",
            "text": "",
            "segments": segments,
            "note": (
                "Whisper model weights are not cached locally and no Gemini API key is active. "
                "Using real FFmpeg audio-activity detection (no fabricated transcript text)."
            ),
        }
