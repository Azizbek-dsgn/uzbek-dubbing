"""Local Uzbek NeMo FastConformer adapter with native word timestamps."""

from pathlib import Path
import subprocess
import tempfile
import wave


def transcribe(path: Path, checkpoint: Path, device: str = "auto", progress=None):
    if not checkpoint.is_file():
        raise RuntimeError(f"FastConformer modeli o‘rnatilmagan: {checkpoint}")
    try:
        import torch
        import nemo.collections.asr as nemo_asr
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("FastConformer uchun subtitles/requirements-fastconformer.txt ni o‘rnating") from exc

    target = "cuda" if device in ("auto", "cuda") and torch.cuda.is_available() else "cpu"
    model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.restore_from(
        str(checkpoint), map_location=target)
    model.eval()
    words = []
    with tempfile.TemporaryDirectory() as temporary:
        wav = Path(temporary) / "audio.wav"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-y", "-loglevel",
                        "error", "-i", str(path), "-ac", "1", "-ar", "16000", str(wav)],
                       check=True)
        with wave.open(str(wav), "rb") as audio:
            rate = audio.getframerate()
            total = audio.getnframes()
            frame_bytes = audio.getsampwidth()
            chunk_frames = rate * 25
            index = 0
            while index < total:
                count = min(chunk_frames, total - index)
                segment = Path(temporary) / "chunk.wav"
                with wave.open(str(segment), "wb") as out:
                    out.setnchannels(1)
                    out.setsampwidth(frame_bytes)
                    out.setframerate(rate)
                    out.writeframes(audio.readframes(count))
                hypotheses = model.transcribe([str(segment)], timestamps=True)
                if hypotheses:
                    stamps = getattr(hypotheses[0], "timestamp", None) or {}
                    rows = stamps.get("word", [])
                    if not rows and getattr(hypotheses[0], "text", "").strip():
                        raise RuntimeError("FastConformer so‘z vaqtlarini qaytarmadi; subtitr yaratilmadi")
                    for row in rows:
                        value = str(row.get("word", "")).strip()
                        if value:
                            start = max(0.0, index / rate + float(row["start"]))
                            end = max(start + 0.01, index / rate + float(row["end"]))
                            words.append((start, end, value))
                index += count
                if progress:
                    progress(index, total)
    return words
