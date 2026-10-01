"""Real FFmpeg decoding + XML editing smoke, with deterministic synthetic mics."""
import sys
import tempfile
import wave
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
# Intel macOS must initialize torch before ONNX/CTranslate2 libraries.
import torch
import numpy as np
from test_podcast import fixture
from subtitles.podcast import run, parse_timeline, track_activity

with tempfile.TemporaryDirectory(prefix='uzscribe-podcast-') as temporary:
    folder=Path(temporary);source=folder/'source.xml';fixture(source,duration=400)
    for mic in range(2):
        samples=np.zeros(18*16000,dtype=np.float32)
        a,b=(2,7) if mic==0 else (10,18)
        t=np.arange((b-a)*16000)/16000
        samples[a*16000:b*16000]=.15*np.sin(2*np.pi*220*t)
        with wave.open(str(folder/f'media {mic}.wav'),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
            audio.writeframes((samples*32767).astype('<i2').tobytes())
    original=source.read_bytes()
    output=folder/'edit.xml'
    report=run(source,output,{'speakers':[{'audio':0,'video':0},{'audio':1,'video':1}]},vad=False)
    assert report['removed_seconds']>2,report
    assert {c['camera'] for c in report['cuts']}=={0,1},report
    result=parse_timeline(output)
    assert result.duration==report['output_frames']
    assert source.read_bytes()==original
    for track in result.audio:
        assert track[0].start==0 and track[-1].end==result.duration
    # Execute bundled ONNX speech detector too; pure silence must stay silent.
    with wave.open(str(folder/'media 0.wav'),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*18*16000)
    levels=track_activity(parse_timeline(source),0,3,vad=True)
    assert np.all(levels<=-99),levels
print('Podcast FFmpeg decode, camera selection, ripple sync and real Silero VAD OK')
