import subprocess
from pathlib import Path

from pydub import AudioSegment

from dubbing.audio_mixer import build_dubbing_track, mux_with_video


def test_build_track_and_mux_with_video(tmp_path: Path):
    segment_audio = tmp_path / "segment.wav"
    AudioSegment.silent(duration=700, frame_rate=24_000).export(segment_audio, format="wav")

    track = build_dubbing_track(
        [{"start_time": 0.4, "end_time": 1.1}],
        [segment_audio],
        tmp_path / "dub.wav",
    )
    source_video = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-shortest", "-c:v", "libx264", "-c:a", "aac", str(source_video),
        ],
        check=True,
        capture_output=True,
    )

    output = mux_with_video(source_video, track, tmp_path / "output.mp4")
    assert output.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert probe.stdout.strip()
