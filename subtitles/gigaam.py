"""Local GigaAM Uzbek ASR with native CTC word timestamps."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path


def _chunks(audio, rate: int, maximum: float = 22.0):
    """Split long speech near a quiet point without changing timeline offsets."""
    import numpy as np

    end = len(audio)
    step = max(1, rate // 50)
    energies = np.array([
        float(np.sqrt(np.mean(np.square(audio[i:min(i + step, end)]))))
        for i in range(0, end, step)
    ])
    quiet = energies < max(0.001, float(np.percentile(energies, 95)) * 0.08)
    silence_cuts = []
    quiet_start = None
    for i, is_quiet in enumerate(np.r_[quiet, False]):
        if is_quiet and quiet_start is None:
            quiet_start = i
        elif not is_quiet and quiet_start is not None:
            if (i - quiet_start) * step / rate >= 0.35:
                silence_cuts.append(int((quiet_start + i) * step / 2))
            quiet_start = None
    start = 0
    while start < end:
        limit = min(end, start + int(maximum * rate))
        candidates = [p for p in silence_cuts if start + 4 * rate <= p < limit
                      and p <= end - 2 * rate]
        if candidates:
            limit = candidates[0]
        elif limit < end:
            low = start + int(0.65 * maximum * rate)
            positions = np.arange(low, limit, step)
            if positions.size:
                limit = int(positions[int(np.argmin(energies[positions // step]))])
        if limit <= start:
            limit = min(end, start + int(maximum * rate))
        yield start / rate, audio[start:limit]
        start = limit


def transcribe(path: Path, base_dir: Path, checkpoint: Path, device: str):
    """Return (start, end, text) tuples, using the model's CTC timing."""
    os.environ.setdefault("HF_HOME", str(base_dir.parent / ".hf-cache"))
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import AutoConfig, AutoModel

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("GigaAM uchun imageio-ffmpeg o'rnatilmagan") from exc
    if not checkpoint.is_file() or not (base_dir / "config.json").is_file():
        raise RuntimeError("GigaAM modeli to'liq o'rnatilmagan")

    # Adobe exports a 16 kHz WAV. Normalize other CLI inputs the same way.
    with tempfile.TemporaryDirectory() as scratch:
        wav = Path(scratch) / "input.wav"
        subprocess.run([ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-i", str(path),
                        "-ac", "1", "-ar", "16000", str(wav)], check=True)
        audio, rate = sf.read(wav, dtype="float32")
        if audio.ndim != 1 or rate != 16000:
            raise RuntimeError("Audio mono 16 kHz formatiga o'tkazilmadi")

        # The downloaded checkpoint contains a state_dict plus plain metadata.
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        config = AutoConfig.from_pretrained(str(base_dir), trust_remote_code=True,
                                           local_files_only=True)
        wrapper = AutoModel.from_config(config, trust_remote_code=True)
        from torch import nn
        if payload["config"]["punctuated"]:
            old = wrapper.model.head.decoder_layers[0]
            vocab = list(payload["vocab"])
            extended = nn.Conv1d(old.in_channels, old.out_channels + 4, kernel_size=1)
            with torch.no_grad():
                extended.weight.zero_()
                extended.bias.fill_(-8.0)
                extended.weight[:old.out_channels - 1] = old.weight[:old.out_channels - 1]
                extended.bias[:old.out_channels - 1] = old.bias[:old.out_channels - 1]
                extended.weight[-1] = old.weight[-1]
                extended.bias[-1] = old.bias[-1]
            wrapper.model.head.decoder_layers[0] = extended
            wrapper.model.decoding.tokenizer.vocab = vocab
            wrapper.model.decoding.blank_id = len(vocab)
        wrapper.model.load_state_dict(payload["model"])
        del payload
        model = wrapper.model.eval()
        target = "mps" if device == "auto" and torch.backends.mps.is_available() else (
            "cuda" if device == "auto" and torch.cuda.is_available() else
            "cpu" if device == "auto" else device)
        model.to(target)
        output = []
        for offset, chunk in _chunks(audio, rate):
            if len(chunk) < rate // 5:
                continue
            signal = torch.from_numpy(np.ascontiguousarray(chunk)).to(target).unsqueeze(0)
            length = torch.tensor([signal.shape[-1]], device=target)
            with torch.inference_mode():
                encoded, encoded_len = model.forward(signal, length)
                _, words = model._decode(encoded, encoded_len, length, True)[0]
            for word in words or []:
                if word.text.strip() and math.isfinite(word.start) and math.isfinite(word.end):
                    output.append((offset + float(word.start), offset + float(word.end), word.text))
        sentence_start = True
        polished = []
        for start, end, text in output:
            if sentence_start and text[:1].isalpha():
                text = text[0].upper() + text[1:]
            polished.append((start, end, text))
            sentence_start = text.rstrip().endswith((".", "?", "!"))
        return polished
