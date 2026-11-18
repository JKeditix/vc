import io
import os
import pytest

from backend.services.analyzer_service import AnalyzerService
from backend.services.editor_service import VideoEditorService
from backend.services.face_tracker import FaceTrackerService
from backend.services.media_service import MediaService
from backend.services.subtitle_service import SubtitleService
from backend.services.transcription_service import TranscriptionService


def test_upload_validation_and_save(tmp_path, sample_video_path):
    assert MediaService.validate_extension("clip.mp4") == ".mp4"
    assert MediaService.validate_extension("demo.MOV") == ".mov"
    assert MediaService.validate_extension("web.webm") == ".webm"

    with pytest.raises(ValueError):
        MediaService.validate_extension("malware.exe")

    with pytest.raises(ValueError):
        MediaService.save_uploaded_file(io.BytesIO(b""), "empty.mp4", "test_empty")

    with open(sample_video_path, "rb") as f:
        saved_path = MediaService.save_uploaded_file(f, "upload_test.mp4", "test_phase1_upload")

    try:
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000
    finally:
        if os.path.exists(saved_path):
            os.remove(saved_path)


def test_probe_audio_extract_and_silence_detection(sample_video_path):
    info = MediaService.probe_video(sample_video_path)
    assert info["width"] == 1280
    assert info["height"] == 720
    assert 9.5 <= info["duration"] <= 10.5
    assert info["has_audio"] is True

    audio_path = MediaService.extract_audio(sample_video_path, "test_phase1_audio")
    try:
        assert os.path.exists(audio_path)
        assert os.path.getsize(audio_path) > 10000

        silences = MediaService.detect_silences(audio_path, duration=info["duration"])
        assert len(silences) >= 1, f"Expected to detect 2.5s silent gap, got: {silences}"

        active = MediaService.compute_active_segments(info["duration"], silences)
        assert len(active) == 2, f"Expected 2 active audio segments around silent gap, got: {active}"
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def test_transcription_never_fabricates_fake_dialogue(sample_video_path):
    audio_path = MediaService.extract_audio(sample_video_path, "test_phase1_stt")
    try:
        result = TranscriptionService.transcribe(sample_video_path, audio_path, 10.0)
        assert "engine" in result
        assert "segments" in result
        assert isinstance(result["segments"], list)
        # Ensure no legacy hardcoded fake sample sentences appear
        combined = " ".join(s.get("text", "") for s in result["segments"]).lower()
        assert "secret viral growth hacks" not in combined
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def test_clip_detection_categories_and_multi_clip_generation():
    # Realistic 3-minute transcript with distinct Hook, Funny, Emotional, and Educational blocks
    segments = [
        {"start": 0.0, "end": 18.0, "text": "Stop scrolling! Why does nobody talk about the real secret behind viral retention?"},
        {"start": 18.0, "end": 36.0, "text": "Wait until you hear step one of this proven 3-step growth framework with real data."},
        {"start": 36.0, "end": 55.0, "text": "Haha that awkward moment when my mic was muted for 20 minutes was hilarious!"},
        {"start": 55.0, "end": 78.0, "text": "Honestly I almost cried because losing everything taught me what hope and love really mean."},
        {"start": 78.0, "end": 105.0, "text": "Here is the exact method: first cut dead air, second highlight key words, third boost audio."},
        {"start": 105.0, "end": 135.0, "text": "Imagine doubling your watch time with one simple mistake fix that anyone can learn today!"},
        {"start": 135.0, "end": 165.0, "text": "Bro the fail at the end was so funny everyone in the studio started laughing!"},
        {"start": 165.0, "end": 195.0, "text": "The truth is consistency changed my life and this final rule gives you huge results."},
    ]
    clips = AnalyzerService.detect_clips(
        transcript_data={"segments": segments},
        total_duration=195.0,
        target_clip_duration=30,
        max_clips=6,
    )
    assert 5 <= len(clips) <= 6, f"Expected 5-6 clips from 3-min video, got {len(clips)}"
    categories = {c["category"] for c in clips}
    assert len(categories) >= 2
    for c in clips:
        assert 0.0 <= c["start_time"] < c["end_time"] <= 195.0
        assert 1 <= c["virality_score"] <= 100
        assert c["title"]


def test_face_tracker_and_animated_subtitles(tmp_path, sample_video_path):
    face_res = FaceTrackerService.track_speaker_center(sample_video_path, 0.0, 5.0, max_samples=5)
    assert face_res["samples_checked"] > 0
    assert 0.0 <= face_res["center_x_ratio"] <= 1.0

    ass_file = str(tmp_path / "test_sub.ass")
    segments = [
        {
            "start": 0.2,
            "end": 3.0,
            "text": "Stop scrolling and see this viral AI secret!",
            "words": [
                {"start": 0.2, "end": 0.6, "word": "Stop"},
                {"start": 0.6, "end": 1.1, "word": "scrolling"},
                {"start": 1.1, "end": 1.4, "word": "and"},
                {"start": 1.4, "end": 1.8, "word": "see"},
                {"start": 1.8, "end": 2.2, "word": "this"},
                {"start": 2.2, "end": 2.6, "word": "viral"},
                {"start": 2.6, "end": 3.0, "word": "secret!"},
            ],
        }
    ]
    count = SubtitleService.generate_animated_ass(segments, 0.0, 4.0, ass_file, aspect_ratio="9:16")
    assert count == 7
    content = open(ass_file, encoding="utf-8").read()
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "\\fscx114\\fscy114" in content


def test_auto_editor_renders_vertical_with_silence_cut_and_other_ratios(sample_video_path):
    transcript = {
        "segments": [
            {"start": 0.3, "end": 3.2, "text": "Stop scrolling! This viral secret works fast."},
            {"start": 6.2, "end": 9.5, "text": "Here is step two of the proven AI strategy."},
        ]
    }

    # 1. Full pipeline 9:16 (1080x1920) with silence removal, transitions, zoom, face track, audio boost, subtitles
    res_916 = VideoEditorService.render_clip(
        source_path=sample_video_path,
        start_time=0.0,
        end_time=10.0,
        clip_id="test_phase1_916",
        aspect_ratio="9:16",
        export_preset="youtube_shorts",
        remove_silence=True,
        burn_subtitles=True,
        enable_zoom=True,
        enable_face_tracking=True,
        enable_transitions=True,
        enhance_audio=True,
        transcript=transcript,
    )
    try:
        assert os.path.exists(res_916["output_path"])
        assert res_916["width"] == 1080
        assert res_916["height"] == 1920
        assert res_916["silence_removed"] is True
        # Original was 10s with 2.5s silence in middle; trimmed output should be noticeably shorter!
        assert 5.5 <= res_916["rendered_duration"] <= 8.5, f"Unexpected trimmed duration: {res_916['rendered_duration']}"
        assert res_916["subtitle_events"] > 0
    finally:
        if os.path.exists(res_916["output_path"]):
            os.remove(res_916["output_path"])

    # 2. Square 1:1 (1080x1080)
    res_11 = VideoEditorService.render_clip(
        source_path=sample_video_path,
        start_time=0.0,
        end_time=3.0,
        clip_id="test_phase1_11",
        aspect_ratio="1:1",
        export_preset="instagram_reels",
        remove_silence=False,
        burn_subtitles=False,
        enable_zoom=False,
        enable_face_tracking=False,
        enable_transitions=False,
        enhance_audio=True,
    )
    try:
        assert res_11["width"] == 1080
        assert res_11["height"] == 1080
    finally:
        if os.path.exists(res_11["output_path"]):
            os.remove(res_11["output_path"])

    # 3. Landscape 16:9 (1920x1080)
    res_169 = VideoEditorService.render_clip(
        source_path=sample_video_path,
        start_time=0.0,
        end_time=3.0,
        clip_id="test_phase1_169",
        aspect_ratio="16:9",
        export_preset="tiktok",
        remove_silence=False,
        burn_subtitles=False,
        enable_zoom=False,
        enable_face_tracking=False,
        enable_transitions=False,
        enhance_audio=False,
    )
    try:
        assert res_169["width"] == 1920
        assert res_169["height"] == 1080
    finally:
        if os.path.exists(res_169["output_path"]):
            os.remove(res_169["output_path"])
