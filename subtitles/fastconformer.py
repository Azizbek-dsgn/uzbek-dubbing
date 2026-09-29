"""Local Uzbek NeMo FastConformer adapter with native word timestamps."""

from pathlib import Path


def transcribe(path: Path, checkpoint: Path, device: str = "auto", progress=None):
    if not checkpoint.is_file():
        raise RuntimeError(f"FastConformer modeli o‘rnatilmagan: {checkpoint}")
    try:
        import torch
        import nemo.collections.asr as nemo_asr
    except ImportError as exc:
        raise RuntimeError("FastConformer uchun subtitles/requirements-fastconformer.txt ni o‘rnating") from exc

    target = "cuda" if device in ("auto", "cuda") and torch.cuda.is_available() else "cpu"
    model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.restore_from(
        str(checkpoint), map_location=target)
    model.eval()
    hypotheses = model.transcribe([str(path)], timestamps=True)
    if not hypotheses:
        return []
    stamps = getattr(hypotheses[0], "timestamp", None) or {}
    rows = stamps.get("word", [])
    if not rows and getattr(hypotheses[0], "text", "").strip():
        raise RuntimeError("FastConformer so‘z vaqtlarini qaytarmadi; subtitr yaratilmadi")
    words = []
    for row in rows:
        value = str(row.get("word", "")).strip()
        if value:
            start = max(0.0, float(row["start"]))
            end = max(start + 0.01, float(row["end"]))
            words.append((start, end, value))
    if progress:
        progress(100, 100)
    return words
