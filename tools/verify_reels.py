"""Actual Uzbek ASR + six retakes + frame-aligned Premiere XML verification."""
import argparse
import sys
import tempfile
import wave
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=ROOT);args=parser.parse_args()
sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(args.runtime.resolve()))
import torch  # Intel native library load order matches installation smoke.
import numpy as np
from test_podcast import fixture
from subtitles.reels import run,render_audio
from subtitles.podcast import parse_timeline

with tempfile.TemporaryDirectory(prefix='uzscribe-reels-check-') as temporary:
    folder=Path(temporary);sample=ROOT/'tests/fixtures/uzbek-take.wav'
    with wave.open(str(sample)) as wav:
        assert wav.getframerate()==16000 and wav.getnchannels()==1 and wav.getsampwidth()==2
        take=wav.readframes(wav.getnframes())
    repeated=b''.join([take+b'\0\0'*16000 for _ in range(6)])
    source_audio=folder/'media 0.wav'
    with wave.open(str(source_audio),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(repeated)
    duration=int(len(repeated)/2/16000*25);source=folder/'source.xml';root=fixture(source,duration=duration,microphones=1)
    for clip in root.findall('.//clipitem'):
        clip.find('in').text='0';clip.find('out').text=str(duration)
    ET.ElementTree(root).write(source)
    original=source.read_bytes()
    settings={'audio':0,'model':'gigaam-uzbek'}
    report=run(source,folder/'reels.xml',settings)
    # CPU/Apple kernels can transcribe Wi-Fi differently at chunk boundaries.
    # Only identical takes should be removed; preserve unmatched speech.
    assert report['removed_retakes']>=3,report
    for candidate in report['retakes']:
        assert candidate['text']==candidate['kept_text'],candidate
    assert report['removed_seconds']>15,report
    assert parse_timeline(folder/'reels.xml').duration==report['output_frames']
    assert source.read_bytes()==original
    settings['keep_retake_ids']=[p['id'] for p in report['retakes']]
    restored=run(source,folder/'restored.xml',settings)
    assert restored['cached_transcript'] and restored['removed_retakes']==0
    assert restored['output_seconds']>report['output_seconds']+9
    # WAV assembly preserves timeline holes and non-zero source offsets.
    timeline=parse_timeline(source);clip=timeline.audio[0][0];clip.start=25;clip.end=125;clip.inside=0;clip.outside=100
    assembled=folder/'assembled.wav';render_audio(timeline,0,0,150,assembled)
    with wave.open(str(assembled)) as wav:
        pcm=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2');assert len(pcm)==96000;assert not pcm[:16000].any();assert pcm[16000:80000].any();assert not pcm[80000:].any()
    print('Actual Uzbek six-take cleanup, cached restore, WAV offsets/gaps and XML sync OK:',report['removed_retakes'],'retakes')
