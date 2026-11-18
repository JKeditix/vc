import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    source_type = Column(String(16), nullable=False)  # 'url' or 'file'
    source_url = Column(Text, nullable=True)
    rights_confirmed = Column(Boolean, default=True, nullable=False)

    file_path = Column(Text, nullable=False, default="")
    audio_path = Column(Text, nullable=True)
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    fps = Column(Float, default=30.0)
    has_audio = Column(Boolean, default=True)

    # Processing preferences
    target_clip_duration = Column(Integer, default=30)  # 15, 30, 45, 60, 90
    max_clips = Column(Integer, default=6)  # 1-10
    aspect_ratio = Column(String(16), default="9:16")  # 9:16, 1:1, 16:9
    export_preset = Column(String(32), default="youtube_shorts")

    # Transcription & pipeline status
    transcript_json = Column(Text, nullable=True)
    transcription_engine = Column(String(64), default="pending")
    status = Column(String(24), default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)
    status_message = Column(String(512), default="Initialized")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    clips = relationship(
        "Clip",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Clip.virality_score.desc()",
    )


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    virality_score = Column(Integer, default=80)
    virality_reason = Column(Text, nullable=True)
    category = Column(String(32), default="Highlight")  # Hook, Funny, Emotional, Educational, Highlight

    # AI Content Generation
    ai_title = Column(String(255), nullable=True)
    ai_description = Column(Text, nullable=True)
    ai_hashtags = Column(Text, nullable=True)
    ai_hook = Column(String(255), nullable=True)
    thumbnail_suggestion = Column(Text, nullable=True)

    # Editing & Export Controls
    aspect_ratio = Column(String(16), default="9:16")  # 9:16, 1:1, 16:9
    export_preset = Column(String(32), default="youtube_shorts")  # youtube_shorts, instagram_reels, tiktok
    remove_silence = Column(Boolean, default=True)
    burn_subtitles = Column(Boolean, default=True)
    enable_zoom = Column(Boolean, default=True)
    enable_face_tracking = Column(Boolean, default=True)
    enable_transitions = Column(Boolean, default=True)
    enhance_audio = Column(Boolean, default=True)

    # Rendered outputs
    output_path = Column(Text, nullable=True)
    thumbnail_path = Column(Text, nullable=True)
    rendered_duration = Column(Float, default=0.0)
    rendered = Column(Boolean, default=False)
    render_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    project = relationship("Project", back_populates="clips")
