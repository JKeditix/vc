import asyncio
import json
import os
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload

from backend.database import SessionLocal, get_db
from backend.models import Project, generate_uuid
from backend.schemas import ProjectOut, serialize_project
from backend.services.media_service import MediaService
from backend.services.pipeline_service import PipelineService
from backend.services.youtube_service import YouTubeService

router = APIRouter(prefix="/api/projects", tags=["Projects"])

VALID_DURATIONS = {15, 30, 45, 60, 90}
VALID_ASPECTS = {"9:16", "1:1", "16:9"}
VALID_PRESETS = {"youtube_shorts", "instagram_reels", "tiktok"}


def _validate_options(
    rights_confirmed: bool,
    target_clip_duration: int,
    max_clips: int,
    aspect_ratio: str,
    export_preset: str,
) -> tuple[int, int, str, str]:
    if not rights_confirmed:
        raise HTTPException(
            status_code=400,
            detail="You must confirm that you own or have permission to process this video.",
        )
    if target_clip_duration not in VALID_DURATIONS:
        raise HTTPException(
            status_code=400,
            detail="target_clip_duration must be one of 15, 30, 45, 60, or 90 seconds.",
        )
    if not (1 <= max_clips <= 10):
        raise HTTPException(status_code=400, detail="max_clips must be between 1 and 10.")
    if aspect_ratio not in VALID_ASPECTS:
        raise HTTPException(status_code=400, detail="aspect_ratio must be 9:16, 1:1, or 16:9.")
    if export_preset not in VALID_PRESETS:
        raise HTTPException(
            status_code=400,
            detail="export_preset must be youtube_shorts, instagram_reels, or tiktok.",
        )
    return target_clip_duration, max_clips, aspect_ratio, export_preset


@router.post("/upload", response_model=ProjectOut)
async def upload_video_project(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rights_confirmed: bool = Form(False),
    target_clip_duration: int = Form(30),
    max_clips: int = Form(6),
    aspect_ratio: str = Form("9:16"),
    export_preset: str = Form("youtube_shorts"),
    db: Session = Depends(get_db),
):
    dur, count, ratio, preset = _validate_options(
        rights_confirmed, target_clip_duration, max_clips, aspect_ratio, export_preset
    )
    original_name = os.path.basename(file.filename or "upload.mp4")
    project_id = generate_uuid()

    try:
        dest_path = await asyncio.to_thread(
            MediaService.save_uploaded_file, file.file, original_name, project_id
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    project = Project(
        id=project_id,
        title=original_name,
        source_type="file",
        rights_confirmed=True,
        file_path=dest_path,
        target_clip_duration=dur,
        max_clips=count,
        aspect_ratio=ratio,
        export_preset=preset,
        status="pending",
        progress=5,
        status_message="Video uploaded. Queued for AI analysis...",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    background_tasks.add_task(PipelineService.run_project_pipeline, project.id, SessionLocal)
    return serialize_project(project, [])


@router.post("/url", response_model=ProjectOut)
async def create_youtube_project(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    rights_confirmed: bool = Form(False),
    target_clip_duration: int = Form(30),
    max_clips: int = Form(6),
    aspect_ratio: str = Form("9:16"),
    export_preset: str = Form("youtube_shorts"),
    db: Session = Depends(get_db),
):
    dur, count, ratio, preset = _validate_options(
        rights_confirmed, target_clip_duration, max_clips, aspect_ratio, export_preset
    )
    try:
        clean_url = YouTubeService.validate_url(url)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    project = Project(
        title="YouTube Video (Downloading...)",
        source_type="url",
        source_url=clean_url,
        rights_confirmed=True,
        file_path="",
        target_clip_duration=dur,
        max_clips=count,
        aspect_ratio=ratio,
        export_preset=preset,
        status="pending",
        progress=5,
        status_message="Queued for YouTube download...",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    background_tasks.add_task(PipelineService.run_project_pipeline, project.id, SessionLocal)
    return serialize_project(project, [])


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = (
        db.query(Project)
        .options(selectinload(Project.clips))
        .order_by(Project.created_at.desc())
        .all()
    )
    return [serialize_project(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .options(selectinload(Project.clips))
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return serialize_project(project)


@router.get("/{project_id}/transcript")
def get_project_transcript(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.transcript_json:
        return {"engine": project.transcription_engine, "text": "", "segments": []}
    return json.loads(project.transcript_json)


@router.post("/{project_id}/retry", response_model=ProjectOut)
def retry_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .options(selectinload(Project.clips))
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    project.status = "pending"
    project.progress = 5
    project.status_message = "Resuming pipeline..."
    db.commit()
    db.refresh(project)

    background_tasks.add_task(PipelineService.run_project_pipeline, project.id, SessionLocal)
    return serialize_project(project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .options(selectinload(Project.clips))
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    files_to_remove = [project.file_path, project.audio_path]
    for clip in project.clips:
        files_to_remove.extend([clip.output_path, clip.thumbnail_path])

    db.delete(project)
    db.commit()

    for path in files_to_remove:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    return {"status": "deleted", "project_id": project_id}
