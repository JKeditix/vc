import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "VIRALCUT AI"
    VERSION: str = "2.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # AI configuration (never exposed via API responses)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Local Whisper configuration (faster-whisper)
    WHISPER_MODEL: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    # Storage & database
    STORAGE_DIR: str = "./viralcut_storage"
    DATABASE_URL: str = ""
    MAX_UPLOAD_MB: int = 2048

    # Allowed upload extensions
    ALLOWED_EXTENSIONS: tuple[str, ...] = (".mp4", ".mov", ".webm")


settings = Settings()


def resolve_path(path_value: str) -> str:
    if os.path.isabs(path_value):
        return path_value
    return os.path.abspath(os.path.join(BASE_DIR, path_value))


STORAGE_DIR = resolve_path(settings.STORAGE_DIR)
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")
CLIPS_DIR = os.path.join(STORAGE_DIR, "clips")
SUBTITLES_DIR = os.path.join(STORAGE_DIR, "subtitles")
THUMBNAILS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def ensure_storage_dirs() -> None:
    for folder in (
        STORAGE_DIR,
        UPLOADS_DIR,
        AUDIO_DIR,
        CLIPS_DIR,
        SUBTITLES_DIR,
        THUMBNAILS_DIR,
    ):
        os.makedirs(folder, exist_ok=True)


ensure_storage_dirs()


def get_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    db_file = os.path.join(BASE_DIR, "viralcut.db").replace("\\", "/")
    return f"sqlite:///{db_file}"
