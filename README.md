# VIRALCUT AI — Automated Shorts & Reels Studio

VIRALCUT AI is a full-stack, modular AI video repurposing engine that turns long-form videos (MP4, MOV, WebM uploads or permitted YouTube URLs) into ready-to-publish **YouTube Shorts**, **Instagram Reels**, and **TikTok** clips at **1080×1920** (plus `1:1` and `16:9`).

## Features

1. **Video Input & Compliance**
   - Upload `MP4`, `MOV`, and `WebM` videos via drag-and-drop or file picker.
   - Paste YouTube URLs (`yt-dlp` download).
   - Built-in content rights confirmation check.
2. **Real AI & Signal Video Analysis**
   - Real audio extraction (`16kHz` mono WAV) & speech transcription via local `faster-whisper` (word-level timestamps) or Gemini multimodal audio API.
   - Detects **Hook**, **Funny**, **Emotional**, **Educational**, and **Highlight** moments with 1–100 viral scores and exact start/end timestamps.
   - Generates up to 5–10 clips from long videos with configurable lengths (`15`, `30`, `45`, `60`, `90` seconds).
3. **Real Automatic FFmpeg + OpenCV Video Editing**
   - OpenCV Haar-cascade **speaker face tracking** for smart vertical/square framing.
   - FFmpeg `silencedetect` **dead-air silence removal** with smooth `xfade` / `acrossfade` transitions.
   - **Animated word-highlighted ASS subtitles** emphasizing active words and key terms.
   - Smooth dynamic zoom and broadcast audio enhancement (`highpass`, `afftdn`, EBU R128 `loudnorm`).
4. **AI Copywriting & Thumbnails**
   - Generates scroll-stopping titles, descriptions, hashtags, opening hooks, and thumbnail suggestions.
   - Extracts and enhances real keyframe thumbnails using FFmpeg + Pillow.
5. **Professional Dark Dashboard & Export**
   - Modern React + Tailwind CSS dark studio interface with live pipeline progress, transcript viewer, inline `<video>` preview, clip editor/re-render modal, individual MP4 download, and bulk ZIP export.

## Project Structure

```text
viralcut_ai/
├── run.py                                # Application entrypoint
├── requirements.txt
├── .env.example
├── .gitignore
├── backend/
│   ├── main.py                           # FastAPI app & static mounts
│   ├── config.py                         # Settings & storage paths
│   ├── database.py                       # SQLite WAL SQLAlchemy engine
│   ├── models.py                         # Project & Clip ORM models
│   ├── schemas.py                        # Pydantic v2 schemas
│   ├── routers/
│   │   ├── projects.py                   # Upload, YouTube URL, transcript, delete
│   │   ├── clips.py                      # Edit/re-render, MP4 download, ZIP bundle
│   │   └── settings.py                   # Masked API key & engine diagnostics
│   └── services/
│       ├── media_service.py              # Upload validation, ffprobe, audio, silencedetect
│       ├── youtube_service.py            # yt-dlp integration
│       ├── transcription_service.py      # faster-whisper + Gemini audio
│       ├── analyzer_service.py           # Gemini + signal viral clip detector
│       ├── face_tracker.py               # OpenCV speaker face tracker
│       ├── subtitle_service.py           # Animated word-highlight ASS subtitles
│       ├── editor_service.py             # FFmpeg editing & platform presets
│       ├── content_service.py            # AI copywriting generator
│       ├── thumbnail_service.py          # FFmpeg + Pillow thumbnail generator
│       └── pipeline_service.py           # End-to-end job orchestrator
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/styles.css
│       └── js/
│           ├── api.js
│           ├── app.jsx
│           └── components/
│               ├── Header.jsx
│               ├── InputPanel.jsx
│               ├── ProgressCard.jsx
│               ├── ClipCard.jsx
│               ├── ClipEditorModal.jsx
│               └── SettingsModal.jsx
└── tests/
    ├── conftest.py
    ├── test_phase1_pipeline.py
    └── test_phase2_full.py
```

## Prerequisites

- **Python 3.10+** (verified on Python 3.12)
- **FFmpeg & FFprobe** installed and available on your system `PATH`

## Installation & Running

1. Copy `.env.example` to `.env` (optional: add your `GEMINI_API_KEY`):
   ```powershell
   copy viralcut_ai\.env.example viralcut_ai\.env
   ```

2. Install Python dependencies:
   ```powershell
   pip install -r viralcut_ai\requirements.txt
   ```

3. Launch VIRALCUT AI:
   ```powershell
   python viralcut_ai\run.py
   ```
   (Or from inside `viralcut_ai/`: `python run.py`)

4. Open `http://localhost:8000` in your browser.

## Running Automated Tests

```powershell
pytest viralcut_ai\tests -v
```
