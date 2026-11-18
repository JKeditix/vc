import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List

from backend.models import Clip, Project
from backend.services.analyzer_service import AnalyzerService
from backend.services.content_service import ContentService
from backend.services.editor_service import VideoEditorService
from backend.services.media_service import MediaService
from backend.services.thumbnail_service import ThumbnailService
from backend.services.transcription_service import TranscriptionService
from backend.services.youtube_service import YouTubeService


class PipelineService:
    """
    Runs the complete end-to-end VIRALCUT AI pipeline inside a background worker:
      1. Video ingest (YouTube yt-dlp with live progress or local upload) & ffprobe metadata
      2. Real transcription (instant YouTube captions -> faster-whisper -> Gemini audio -> audio-activity)
      3. AI clip detection & virality scoring
      4. AI content generation (titles, descriptions, hashtags, hooks, thumbnail ideas)
      5. Parallel FFmpeg editing + OpenCV face tracking + animated subtitles + thumbnail generation
    """

    @staticmethod
    def run_project_pipeline(project_id: str, session_factory: Callable) -> None:
        db = session_factory()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return

            def update_status(progress: int, message: str) -> None:
                project.progress = max(0, min(100, int(progress)))
                project.status_message = message[:500]
                db.commit()

            project.status = "processing"
            update_status(8, "Preparing video source...")

            # Clean up any partial clips from an interrupted previous attempt
            db.query(Clip).filter(Clip.project_id == project.id).delete()
            db.commit()

            # 1. Ingest & probe video (reuse already-downloaded file on retry)
            if project.source_type == "url" and not (project.file_path and os.path.exists(project.file_path)):
                def on_dl_progress(ratio: float, msg: str) -> None:
                    update_status(10 + int(ratio * 18), msg)

                def on_meta(meta: dict) -> None:
                    if meta.get("title"):
                        project.title = meta["title"]
                        db.commit()

                info = YouTubeService.download_video(
                    project.source_url,
                    project.id,
                    progress_callback=on_dl_progress,
                    metadata_callback=on_meta,
                )
                project.file_path = info["file_path"]
                project.title = info["title"]
            else:
                update_status(18, "Inspecting video streams...")
                info = MediaService.probe_video(project.file_path)

            project.duration = info["duration"]
            project.width = info["width"]
            project.height = info["height"]
            project.fps = info["fps"]
            project.has_audio = info["has_audio"]
            update_status(30, "Video ready. Fetching captions / transcription...")

            # 2. Try fast YouTube captions first (avoids slow WAV extraction on 2-hour YouTube videos)
            def on_transcribe_progress(ratio: float, msg: str) -> None:
                update_status(32 + int(ratio * 24), msg)

            transcript_data = None
            if project.source_type == "url" and project.source_url:
                transcript_data = YouTubeService.fetch_captions(project.source_url, project.id)

            if not transcript_data:
                audio_path = None
                if project.has_audio:
                    update_status(32, "Extracting 16kHz audio track for transcription...")
                    audio_path = MediaService.extract_audio(project.file_path, project.id)
                    project.audio_path = audio_path
                    update_status(38, "Audio extracted. Transcribing speech...")

                transcript_data = TranscriptionService.transcribe(
                    video_path=project.file_path,
                    audio_path=audio_path,
                    duration=project.duration,
                    progress_callback=on_transcribe_progress,
                    source_url=None,
                    project_id=project.id,
                )

            project.transcript_json = json.dumps(transcript_data, ensure_ascii=False)
            project.transcription_engine = transcript_data.get("engine", "unknown")
            update_status(58, "Transcription complete. Scoring viral highlights...")

            # 3. Viral clip detection & scoring
            detected_clips = AnalyzerService.detect_clips(
                transcript_data=transcript_data,
                total_duration=project.duration,
                target_clip_duration=project.target_clip_duration,
                max_clips=project.max_clips,
            )
            if not detected_clips:
                raise RuntimeError("No valid clip segments could be extracted from this video.")

            update_status(66, f"Generating AI copywriting & editing {len(detected_clips)} shorts...")

            # 4. Create Clip rows first
            video_meta = {
                "width": project.width,
                "height": project.height,
                "fps": project.fps,
                "duration": project.duration,
                "has_audio": project.has_audio,
            }
            clip_rows: List[Clip] = []
            for raw_clip in detected_clips:
                enriched = ContentService.enrich_clip_content(raw_clip, project_title=project.title)
                clip = Clip(
                    project_id=project.id,
                    title=enriched["title"],
                    summary=enriched["summary"],
                    start_time=enriched["start_time"],
                    end_time=enriched["end_time"],
                    duration=enriched["duration"],
                    virality_score=enriched["virality_score"],
                    virality_reason=enriched["virality_reason"],
                    category=enriched["category"],
                    ai_title=enriched["ai_title"],
                    ai_description=enriched["ai_description"],
                    ai_hashtags=enriched["ai_hashtags"],
                    ai_hook=enriched["ai_hook"],
                    thumbnail_suggestion=enriched["thumbnail_suggestion"],
                    aspect_ratio=project.aspect_ratio,
                    export_preset=project.export_preset,
                    remove_silence=True,
                    burn_subtitles=True,
                    enable_zoom=True,
                    enable_face_tracking=True,
                    enable_transitions=True,
                    enhance_audio=True,
                )
                db.add(clip)
                clip_rows.append(clip)
            db.commit()

            # 5. Render clips in parallel (2 workers) for 2x faster turnaround
            total_clips = len(clip_rows)
            source_path = project.file_path

            def _render_one(clip_spec: Dict) -> Dict:
                render_res = VideoEditorService.render_clip(
                    source_path=source_path,
                    start_time=clip_spec["start_time"],
                    end_time=clip_spec["end_time"],
                    clip_id=clip_spec["id"],
                    aspect_ratio=clip_spec["aspect_ratio"],
                    export_preset=clip_spec["export_preset"],
                    remove_silence=True,
                    burn_subtitles=True,
                    enable_zoom=True,
                    enable_face_tracking=True,
                    enable_transitions=True,
                    enhance_audio=True,
                    transcript=transcript_data,
                    video_info=video_meta,
                )
                thumb_path = ThumbnailService.generate_thumbnail(
                    video_path=render_res["output_path"],
                    clip_id=clip_spec["id"],
                    headline=clip_spec["headline"],
                    category=clip_spec["category"],
                    virality_score=clip_spec["virality_score"],
                )
                return {
                    "clip_id": clip_spec["id"],
                    "output_path": render_res["output_path"],
                    "rendered_duration": render_res["rendered_duration"],
                    "thumbnail_path": thumb_path,
                }

            specs = [
                {
                    "id": c.id,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "aspect_ratio": c.aspect_ratio,
                    "export_preset": c.export_preset,
                    "headline": c.ai_title or c.title,
                    "category": c.category,
                    "virality_score": c.virality_score,
                }
                for c in clip_rows
            ]
            clip_map = {c.id: c for c in clip_rows}
            completed = 0

            with ThreadPoolExecutor(max_workers=2) as pool:
                future_to_id = {pool.submit(_render_one, spec): spec["id"] for spec in specs}
                for fut in as_completed(future_to_id):
                    cid = future_to_id[fut]
                    clip_obj = clip_map[cid]
                    completed += 1
                    try:
                        res = fut.result()
                        clip_obj.output_path = res["output_path"]
                        clip_obj.rendered_duration = res["rendered_duration"]
                        clip_obj.rendered = True
                        clip_obj.render_error = None
                        if res["thumbnail_path"] and os.path.exists(res["thumbnail_path"]):
                            clip_obj.thumbnail_path = res["thumbnail_path"]
                    except Exception as render_err:
                        clip_obj.rendered = False
                        clip_obj.render_error = str(render_err)

                    update_status(
                        min(99, 66 + int((completed / total_clips) * 33)),
                        f"Rendered {completed}/{total_clips} short clips...",
                    )

            project.status = "completed"
            update_status(100, f"Completed! {total_clips} short clip(s) ready.")

        except Exception as err:
            db.rollback()
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "failed"
                project.status_message = str(err)[:500]
                db.commit()
        finally:
            db.close()
