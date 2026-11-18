import asyncio
import json
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import CLIPS_DIR
from backend.database import get_db
from backend.models import Clip, Project
from backend.schemas import ClipOut, ClipRenderRequest, serialize_clip
from backend.services.editor_service import VideoEditorService
from backend.services.media_service import sanitize_filename
from backend.services.thumbnail_service import ThumbnailService

router = APIRouter(prefix="/api/clips", tags=["Clips"])


@router.post("/{clip_id}/render", response_model=ClipOut)
async def render_or_update_clip(
    clip_id: str,
    options: ClipRenderRequest,
    db: Session = Depends(get_db),
):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    project = db.query(Project).filter(Project.id == clip.project_id).first()
    if not project or not project.file_path or not os.path.exists(project.file_path):
        raise HTTPException(status_code=404, detail="Source video file is missing.")

    new_start = clip.start_time if options.start_time is None else float(options.start_time)
    new_end = clip.end_time if options.end_time is None else float(options.end_time)
    if project.duration > 0:
        new_start = max(0.0, min(new_start, max(0.0, project.duration - 0.5)))
        new_end = max(new_start + 0.5, min(new_end, project.duration))

    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time.")

    transcript_data = json.loads(project.transcript_json) if project.transcript_json else None
    video_meta = {
        "width": project.width,
        "height": project.height,
        "fps": project.fps,
        "duration": project.duration,
        "has_audio": project.has_audio,
    }

    try:
        render_res = await asyncio.to_thread(
            VideoEditorService.render_clip,
            project.file_path,
            new_start,
            new_end,
            clip.id,
            options.aspect_ratio,
            options.export_preset,
            options.remove_silence,
            options.burn_subtitles,
            options.enable_zoom,
            options.enable_face_tracking,
            options.enable_transitions,
            options.enhance_audio,
            transcript_data,
            video_meta,
        )
        thumb_path = await asyncio.to_thread(
            ThumbnailService.generate_thumbnail,
            render_res["output_path"],
            clip.id,
            clip.ai_title or clip.title,
            clip.category,
            clip.virality_score,
        )
    except Exception as err:
        clip.render_error = str(err)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Clip render failed: {str(err)}") from err

    clip.start_time = round(new_start, 2)
    clip.end_time = round(new_end, 2)
    clip.duration = round(new_end - new_start, 2)
    clip.aspect_ratio = options.aspect_ratio
    clip.export_preset = options.export_preset
    clip.remove_silence = options.remove_silence
    clip.burn_subtitles = options.burn_subtitles
    clip.enable_zoom = options.enable_zoom
    clip.enable_face_tracking = options.enable_face_tracking
    clip.enable_transitions = options.enable_transitions
    clip.enhance_audio = options.enhance_audio
    clip.output_path = render_res["output_path"]
    clip.rendered_duration = render_res["rendered_duration"]
    clip.rendered = True
    clip.render_error = None
    if thumb_path and os.path.exists(thumb_path):
        clip.thumbnail_path = thumb_path

    db.commit()
    db.refresh(clip)
    return serialize_clip(clip)


@router.get("/{clip_id}/download")
def download_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.output_path or not os.path.exists(clip.output_path):
        raise HTTPException(status_code=404, detail="Rendered clip file is not ready.")

    safe_title = sanitize_filename(clip.title, f"clip_{clip.id[:8]}")
    filename = f"viralcut_{clip.export_preset}_{safe_title}_{clip.id[:6]}.mp4"
    return FileResponse(clip.output_path, media_type="video/mp4", filename=filename)


@router.get("/project/{project_id}/download-all")
async def download_project_zip(project_id: str, db: Session = Depends(get_db)):
    clips = (
        db.query(Clip)
        .filter(Clip.project_id == project_id, Clip.rendered == True)  # noqa: E712
        .order_by(Clip.virality_score.desc())
        .all()
    )
    ready_clips = [c for c in clips if c.output_path and os.path.exists(c.output_path)]
    if not ready_clips:
        raise HTTPException(status_code=404, detail="No rendered clips available for ZIP export.")

    os.makedirs(CLIPS_DIR, exist_ok=True)
    zip_path = os.path.join(CLIPS_DIR, f"viralcut_bundle_{project_id[:8]}.zip")

    def _create_zip() -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, clip in enumerate(ready_clips, start=1):
                safe_title = sanitize_filename(clip.title, f"clip_{idx}")
                arc = f"{idx:02d}_Score{clip.virality_score}_{clip.category}_{safe_title}.mp4"
                zf.write(clip.output_path, arcname=arc)

    await asyncio.to_thread(_create_zip)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"viralcut_shorts_{project_id[:8]}.zip",
    )
