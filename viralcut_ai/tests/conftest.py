import os
import subprocess
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def sample_video_path(tmp_path_factory) -> str:
    """
    Generate a real 10-second 1280x720 MP4 test video with two audible segments
    separated by a genuine 2.5-second silent pause so silence detection, trimming,
    xfade transitions, subtitles, and 1080x1920 rendering are tested for real.
    """
    out_dir = tmp_path_factory.mktemp("fixtures")
    video_path = str(out_dir / "sample_talk.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=1280x720:rate=30:duration=10",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=3.5",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=48000:cl=mono:d=2.5",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=523:sample_rate=48000:duration=4.0",
        "-filter_complex",
        "[1:a][2:a][3:a]concat=n=3:v=0:a=1[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        video_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Failed to build sample video: {res.stderr}"
    assert os.path.exists(video_path)
    return video_path
