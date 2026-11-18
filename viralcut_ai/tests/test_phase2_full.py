import asyncio
import io
import zipfile
import httpx

from backend.config import settings
from backend.database import init_db
from backend.main import app


def _run(coro):
    return asyncio.run(coro)


def _client():
    init_db()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_frontend_and_static_assets_served():
    async def _inner():
        async with _client() as client:
            health = await client.get("/api/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            home = await client.get("/")
            assert home.status_code == 200
            assert "VIRALCUT AI" in home.text

            for asset in (
                "/static/css/styles.css",
                "/static/js/api.js",
                "/static/js/app.jsx",
                "/static/js/components/Header.jsx",
                "/static/js/components/InputPanel.jsx",
                "/static/js/components/ProgressCard.jsx",
                "/static/js/components/ClipCard.jsx",
                "/static/js/components/ClipEditorModal.jsx",
                "/static/js/components/SettingsModal.jsx",
            ):
                r = await client.get(asset)
                assert r.status_code == 200, f"Static asset missing: {asset}"

    _run(_inner())


def test_settings_never_exposes_raw_api_key():
    original_key = settings.GEMINI_API_KEY

    async def _inner():
        async with _client() as client:
            res = await client.get("/api/settings")
            assert res.status_code == 200
            data = res.json()
            assert data["ffmpeg_available"] is True
            assert data["faster_whisper_available"] is True
            assert data["opencv_available"] is True
            assert "gemini_api_key" not in data

            secret = "AIzaSy_TEST_SECRET_DO_NOT_EXPOSE_12345"
            upd = await client.post("/api/settings", json={"gemini_api_key": secret})
            assert upd.status_code == 200
            assert upd.json()["has_gemini_api_key"] is True
            assert secret not in upd.text

            await client.post("/api/settings", json={"gemini_api_key": original_key})

    try:
        _run(_inner())
    finally:
        settings.GEMINI_API_KEY = original_key


def test_validation_guards_rights_and_youtube_url():
    async def _inner():
        async with _client() as client:
            r1 = await client.post(
                "/api/projects/url",
                data={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "rights_confirmed": "false",
                },
            )
            assert r1.status_code == 400
            assert "permission" in r1.json()["detail"].lower()

            r2 = await client.post(
                "/api/projects/url",
                data={
                    "url": "https://example.com/not-youtube",
                    "rights_confirmed": "true",
                },
            )
            assert r2.status_code == 400

    _run(_inner())


def test_full_end_to_end_upload_pipeline_rerender_download_and_cleanup(sample_video_path):
    async def _inner():
        async with _client() as client:
            with open(sample_video_path, "rb") as f:
                upload_res = await client.post(
                    "/api/projects/upload",
                    files={"file": ("creator_demo.mp4", f, "video/mp4")},
                    data={
                        "rights_confirmed": "true",
                        "target_clip_duration": "15",
                        "max_clips": "5",
                        "aspect_ratio": "9:16",
                        "export_preset": "youtube_shorts",
                    },
                )
            assert upload_res.status_code == 200, upload_res.text
            project_id = upload_res.json()["id"]

            proj_res = await client.get(f"/api/projects/{project_id}")
            assert proj_res.status_code == 200
            project = proj_res.json()
            assert project["status"] == "completed", f"Pipeline failed: {project['status_message']}"
            assert project["progress"] == 100
            assert project["width"] == 1280
            assert project["height"] == 720
            assert len(project["clips"]) >= 1

            tr_res = await client.get(f"/api/projects/{project_id}/transcript")
            assert tr_res.status_code == 200
            assert "segments" in tr_res.json()

            clip = project["clips"][0]
            clip_id = clip["id"]
            assert clip["rendered"] is True
            assert clip["ai_title"]
            assert clip["ai_description"]
            assert clip["ai_hashtags"]
            assert clip["ai_hook"]
            assert clip["thumbnail_suggestion"]
            assert clip["media_url"]
            assert clip["thumbnail_url"]

            media_clip = await client.get(clip["media_url"])
            assert media_clip.status_code == 200
            assert len(media_clip.content) > 5000

            media_thumb = await client.get(clip["thumbnail_url"])
            assert media_thumb.status_code == 200
            assert media_thumb.content[:2] == b"\xff\xd8"

            rerender_res = await client.post(
                f"/api/clips/{clip_id}/render",
                json={
                    "start_time": 0.0,
                    "end_time": 4.0,
                    "aspect_ratio": "1:1",
                    "export_preset": "instagram_reels",
                    "remove_silence": False,
                    "burn_subtitles": True,
                    "enable_zoom": True,
                    "enable_face_tracking": True,
                    "enable_transitions": True,
                    "enhance_audio": True,
                },
            )
            assert rerender_res.status_code == 200, rerender_res.text
            updated_clip = rerender_res.json()
            assert updated_clip["aspect_ratio"] == "1:1"
            assert updated_clip["export_preset"] == "instagram_reels"
            assert updated_clip["rendered"] is True

            dl_res = await client.get(f"/api/clips/{clip_id}/download")
            assert dl_res.status_code == 200
            assert dl_res.headers["content-type"] == "video/mp4"
            assert len(dl_res.content) > 5000

            zip_res = await client.get(f"/api/clips/project/{project_id}/download-all")
            assert zip_res.status_code == 200
            assert zip_res.headers["content-type"] == "application/zip"
            with zipfile.ZipFile(io.BytesIO(zip_res.content)) as zf:
                names = zf.namelist()
                assert len(names) >= 1
                assert all(n.endswith(".mp4") for n in names)

            del_res = await client.delete(f"/api/projects/{project_id}")
            assert del_res.status_code == 200
            assert (await client.get(f"/api/projects/{project_id}")).status_code == 404

    _run(_inner())
