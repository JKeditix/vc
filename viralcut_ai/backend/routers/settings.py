import importlib.util
import shutil

from fastapi import APIRouter

from backend.config import settings
from backend.schemas import SettingsResponse, SettingsUpdateRequest
from backend.services.face_tracker import FaceTrackerService

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _build_settings_response() -> SettingsResponse:
    return SettingsResponse(
        has_gemini_api_key=bool((settings.GEMINI_API_KEY or "").strip()),
        gemini_model=settings.GEMINI_MODEL,
        whisper_model=settings.WHISPER_MODEL,
        ffmpeg_available=bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        faster_whisper_available=importlib.util.find_spec("faster_whisper") is not None,
        opencv_available=FaceTrackerService.is_available(),
    )


@router.get("", response_model=SettingsResponse)
def get_settings():
    """Return engine status and whether a Gemini key is set. Never exposes raw API keys."""
    return _build_settings_response()


@router.post("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest):
    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key.strip()
    if payload.gemini_model:
        settings.GEMINI_MODEL = payload.gemini_model.strip()
    if payload.whisper_model:
        settings.WHISPER_MODEL = payload.whisper_model.strip()
    return _build_settings_response()
