import os
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AspectRatio = Literal["9:16", "1:1", "16:9"]
ExportPreset = Literal["youtube_shorts", "instagram_reels", "tiktok"]
ClipDurationChoice = Literal[15, 30, 45, 60, 90]


class ClipRenderRequest(BaseModel):
    start_time: Optional[float] = Field(default=None, ge=0.0)
    end_time: Optional[float] = Field(default=None, gt=0.0)
    aspect_ratio: AspectRatio = "9:16"
    export_preset: ExportPreset = "youtube_shorts"
    remove_silence: bool = True
    burn_subtitles: bool = True
    enable_zoom: bool = True
    enable_face_tracking: bool = True
    enable_transitions: bool = True
    enhance_audio: bool = True


class SettingsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    whisper_model: Optional[str] = None


class SettingsResponse(BaseModel):
    has_gemini_api_key: bool
    gemini_model: str
    whisper_model: str
    ffmpeg_available: bool
    faster_whisper_available: bool
    opencv_available: bool


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    summary: Optional[str] = None
    start_time: float
    end_time: float
    duration: float
    virality_score: int
    virality_reason: Optional[str] = None
    category: str

    ai_title: Optional[str] = None
    ai_description: Optional[str] = None
    ai_hashtags: Optional[str] = None
    ai_hook: Optional[str] = None
    thumbnail_suggestion: Optional[str] = None

    aspect_ratio: str
    export_preset: str
    remove_silence: bool
    burn_subtitles: bool
    enable_zoom: bool
    enable_face_tracking: bool
    enable_transitions: bool
    enhance_audio: bool

    rendered: bool
    rendered_duration: float = 0.0
    render_error: Optional[str] = None
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_type: str
    source_url: Optional[str] = None
    rights_confirmed: bool
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool

    target_clip_duration: int
    max_clips: int
    aspect_ratio: str
    export_preset: str

    transcription_engine: str
    status: str
    progress: int
    status_message: str
    created_at: Optional[datetime] = None
    clips: List[ClipOut] = []


def serialize_clip(clip) -> ClipOut:
    data = ClipOut.model_validate(clip)
    if clip.rendered and clip.output_path and os.path.exists(clip.output_path):
        data.media_url = f"/media/clips/{os.path.basename(clip.output_path)}"
    if clip.thumbnail_path and os.path.exists(clip.thumbnail_path):
        data.thumbnail_url = f"/media/thumbnails/{os.path.basename(clip.thumbnail_path)}"
    return data


def serialize_project(project, clips=None) -> ProjectOut:
    data = ProjectOut.model_validate(project)
    clip_list = clips if clips is not None else getattr(project, "clips", [])
    data.clips = [serialize_clip(c) for c in clip_list]
    return data
