"""UzScribe Podcast: speech-driven, frame-accurate edits of Premiere FCP7 XML.

The editor works on an exported, already synchronized timeline. Microphone
activity selects camera tracks; speech detection does not depend on ASR language.
Only the new XML is written. Source media and the original sequence are retained.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse

# ONNX Runtime 1.29+ telemetry can abort macOS during native shutdown.
# Local transcription needs no telemetry; opt out before runtime initialization.
os.environ['ORT_DISABLE_TELEMETRY'] = '1'

import numpy as np


@dataclass
class Clip:
    element: ET.Element
    start: int
    end: int
    inside: int
    outside: int
    fps: Fraction
    file: ET.Element
    path: Path | None
    channel: int
    enabled: bool = True


@dataclass
class Timeline:
    sequence: ET.Element
    fps: Fraction
    duration: int
    video: list[list[Clip]]
    audio: list[list[Clip]]


def rate(element: ET.Element | None, fallback: Fraction = Fraction(25)) -> Fraction:
    if element is None:
        return fallback
    base = int(element.findtext('timebase', str(round(float(fallback)))))
    if not 1 <= base <= 120:
        raise ValueError('Timeline FPS noto‘g‘ri.')
    return Fraction(base * 1000, 1001) if element.findtext('ntsc', 'FALSE').upper() == 'TRUE' else Fraction(base)


def media_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != 'file':
        raise ValueError('Podcast uchun lokal media fayllari kerak.')
    result = unquote(parsed.path)
    if re.match(r'^/[A-Za-z]:/', result):
        result = result[1:]
    if parsed.netloc and parsed.netloc.lower() != 'localhost':
        result = '//' + parsed.netloc + '/' + result.lstrip('/')
    return Path(result)


def parse_timeline(path: Path, *, allow_transitions: bool = False) -> Timeline:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != 'xmeml':
        raise ValueError('Premiere’dan eksport qilingan FCP7 XML kerak.')
    sequences = [s for s in root.iter('sequence') if s.find('media') is not None]
    if len(sequences) != 1:
        raise ValueError('Bitta, flatten qilingan sequence kerak. Nested/multicam kliplarni avval flatten qiling.')
    sequence = sequences[0]
    fps = rate(sequence.find('rate'))
    duration = int(sequence.findtext('duration', '0'))
    if duration <= 0:
        raise ValueError('Sequence bo‘sh.')
    files = {f.get('id'): f for f in root.iter('file') if f.findtext('pathurl') or f.findtext('mediaSource')}
    streams = []
    for kind in ('video', 'audio'):
        tracks = []
        for track in sequence.findall('media/' + kind + '/track'):
            if track.find('transitionitem') is not None and not allow_transitions:
                raise ValueError('Transition bor. Podcast montajini transition qo‘shishdan oldin bajaring.')
            clips = []
            items = list(track)
            for element in track.findall('clipitem'):
                if element.find('sequence') is not None:
                    raise ValueError('Nested klipni avval flatten qiling.')
                if any((e.findtext('effectid', '').lower() in {'timeremap', 'speed', 'time-remap'})
                       for e in element.findall('filter/effect')):
                    raise ValueError('Speed/time-remap ishlatilgan kliplar hozir qo‘llanmaydi.')
                file = element.find('file')
                if file is None:
                    raise ValueError('Klipning media manbasi topilmadi.')
                file = file if file.findtext('pathurl') or file.findtext('mediaSource') else files.get(file.get('id'))
                if file is None:
                    raise ValueError('XML media havolasi yechilmadi: ' + element.findtext('name', 'Nomsiz klip'))
                if not file.findtext('pathurl') and kind != 'video':
                    raise ValueError('Nutq uchun lokal audio fayli kerak.')
                clip_rate = rate(element.find('rate'), rate(file.find('rate'), fps))
                start, end, inside, outside = (int(element.findtext(k, '-1'))
                                              for k in ('start', 'end', 'in', 'out'))
                if allow_transitions:
                    position = items.index(element)
                    if start == -1 and position > 0 and items[position-1].tag == 'transitionitem':
                        start = int(items[position-1].findtext('start', '-1'))
                    if end == -1 and position+1 < len(items) and items[position+1].tag == 'transitionitem':
                        end = int(items[position+1].findtext('end', '-1'))
                if not 0 <= start < end <= duration or not 0 <= inside < outside:
                    raise ValueError('Klip vaqtlari noto‘g‘ri yoki transition bilan bog‘langan.')
                if abs(float(Fraction(outside - inside, 1) / clip_rate - Fraction(end - start, 1) / fps)) > 2 / float(fps):
                    raise ValueError('Klip tezligi 100% emas. Avval normal tezlikdagi timeline tayyorlang.')
                channel = max(0, int(element.findtext('sourcetrack/trackindex', '1')) - 1)
                clips.append(Clip(element, start, end, inside, outside, clip_rate,
                                  file, media_path(file.findtext('pathurl')) if file.findtext('pathurl') else None, channel,
                                  track.findtext('enabled', 'TRUE').upper() != 'FALSE' and
                                  element.findtext('enabled', 'TRUE').upper() != 'FALSE'))
            tracks.append(clips)
        streams.append(tracks)
    return Timeline(sequence, fps, duration, streams[0], streams[1])


@lru_cache(maxsize=128)
def _audio_stream_channels(path: str, size: int, modified: int) -> tuple[int, ...]:
    import av
    try:
        with av.open(path) as container:
            return tuple(len(stream.codec_context.layout.channels) for stream in container.streams.audio)
    except (OSError, ValueError) as exc:
        raise ValueError('Audio media o‘qilmadi: ' + Path(path).name) from exc


def audio_route(clip: Clip) -> tuple[int, int]:
    """Resolve Premiere's split mono XML components to real stream/channel pairs."""
    if clip.path is None or not clip.path.is_file():
        raise ValueError('Media offline yoki topilmadi: ' + (clip.path.name if clip.path else 'Audio'))
    components = clip.file.findall('media/audio')
    declared = [int(channel.findtext('sourcechannel', '0')) - 1
                for component in components for channel in component.findall('audiochannel')]
    physical = declared[clip.channel] if len(declared) > clip.channel and declared[clip.channel] >= 0 else clip.channel
    stat = clip.path.stat()
    counts = _audio_stream_channels(str(clip.path), stat.st_size, stat.st_mtime_ns)
    remaining = physical
    for stream, count in enumerate(counts):
        if remaining < count:
            return stream, remaining
        remaining -= count
    raise ValueError(f'{clip.path.name}: manba audio kanali {physical + 1} topilmadi ({sum(counts)} kanal bor).')


def track_activity(timeline: Timeline, track_index: int, step: int, *, vad: bool = True, neural: bool = False) -> np.ndarray:
    """Decode bounded chunks. Neural cleanup retains quiet speech; cameras use loudness."""
    import imageio_ffmpeg
    if not 0 <= track_index < len(timeline.audio):
        raise ValueError('Tanlangan mikrofon treki topilmadi.')
    levels = np.full(math.ceil(timeline.duration / step), -100.0, dtype=np.float32)
    if not any(c.enabled for c in timeline.audio[track_index]):
        raise ValueError(f'Audio {track_index + 1} treki bo‘sh yoki o‘chirilgan.')
    speech = None
    if vad:
        from faster_whisper.vad import get_speech_timestamps
        speech = get_speech_timestamps
    fps = float(timeline.fps)
    samples_per_window = max(1, round(16000 * step / fps))
    for clip in timeline.audio[track_index]:
        if not clip.enabled:
            continue
        if not clip.path.is_file():
            raise ValueError(f'Media offline yoki topilmadi: {clip.path.name}')
        seconds = (clip.end - clip.start) / fps
        audio_stream, audio_channel = audio_route(clip)
        command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error',
                   '-ss', str(float(Fraction(clip.inside, 1) / clip.fps)), '-i', str(clip.path),
                   '-t', str(seconds), '-map', f'0:a:{audio_stream}', '-vn',
                   '-af', f'pan=mono|c0=c{audio_channel}', '-ar', '16000', '-f', 'f32le', 'pipe:1']
        # A file for stderr prevents an unread stderr pipe from blocking ffmpeg.
        import tempfile
        with tempfile.TemporaryFile() as error:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=error)
            consumed = 0
            context = np.empty(0, dtype=np.float32)
            block_bytes = samples_per_window * 300 * 4
            try:
                pending = process.stdout.read(block_bytes)
                while True:
                    data = pending
                    pending = process.stdout.read(block_bytes)
                    if not data:
                        break
                    audio = np.frombuffer(data, dtype='<f4')
                    mask = np.ones(len(audio), dtype=bool)
                    if speech:
                        mask[:] = False
                        if neural:
                            # Half a second on both sides avoids resetting VAD at a word.
                            following = np.frombuffer(pending, dtype='<f4')[:8000]
                            detection = np.concatenate((context, audio, following))
                            peak = float(np.percentile(np.abs(detection), 99.5))
                            if peak > 1e-5:
                                detection = detection * min(8.0, max(1.0, .1/peak))
                            turns = speech(detection, sampling_rate=16000, threshold=.35,
                                           min_silence_duration_ms=120, speech_pad_ms=120)
                            offset = len(context)
                        else:
                            turns = speech(audio, sampling_rate=16000)
                            offset = 0
                        for turn in turns:
                            a, b = max(0, turn['start']-offset), min(len(audio), turn['end']-offset)
                            if b > a:
                                mask[a:b] = True
                    for start in range(0, len(audio), samples_per_window):
                        end = min(len(audio), start + samples_per_window)
                        if not mask[start:end].any():
                            continue
                        rms = float(np.sqrt(np.mean(np.square(audio[start:end]))))
                        frame = clip.start + round((consumed + start) / 16000 * fps)
                        index = frame // step
                        if 0 <= index < len(levels):
                            levels[index] = max(levels[index], -5.0 if neural and speech else 20 * math.log10(max(rms, 1e-5)))
                    context = audio[-8000:]
                    consumed += len(audio)
                code = process.wait()
                if code:
                    error.seek(0)
                    raise ValueError('Audio o‘qilmadi: ' + error.read().decode('utf-8', 'replace')[-800:])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
    return levels


def speech_activity(timeline: Timeline, selected: int, step: int, inside: int, outside: int,
                    threshold: float, *, vad: bool = True, allow_sibling: bool = True, neural: bool = False):
    def audible(levels):
        return np.any(levels[inside // step:math.ceil(outside / step)] > threshold)
    options = {'vad': vad, **({'neural': True} if neural else {})}
    levels = track_activity(timeline, selected, step, **options)
    if audible(levels) or not allow_sibling:
        return selected, levels, ''
    def signature(track):
        return [(str(c.path), c.start, c.end, c.inside, c.outside, c.fps) for c in track if c.enabled]
    selected_signature = signature(timeline.audio[selected])
    # Only a paired channel of the exact same synced clips can replace this input.
    # Never select unrelated music or another speaker's microphone.
    if selected_signature:
        for index, track in enumerate(timeline.audio):
            if index == selected or signature(track) != selected_signature:
                continue
            alternative = track_activity(timeline, index, step, **options)
            if audible(alternative):
                return index, alternative, f'Audio {selected + 1} kanalida nutq yo‘q; shu klipning nutqli Audio {index + 1} kanali ishlatildi.'
    return selected, levels, ''


def camera_plan(levels: np.ndarray, *, step: int, duration: int, fps: float,
                threshold: float = -42, minimum_shot: float = 2.5,
                reaction: float = 0.35, margin: float = 3, wide: bool = False,
                wide_every: float = 30) -> list[dict]:
    """Return stable speaker/wide shots plus silence indicators on frame grid."""
    if levels.ndim != 2 or not len(levels) or levels.shape[1] != math.ceil(duration / step):
        raise ValueError('Mikrofon tahlili o‘lchami noto‘g‘ri.')
    if not np.isfinite(levels).all():
        raise ValueError('Audio tahlilida noto‘g‘ri qiymat bor.')
    peaks = np.percentile(levels, 95, axis=1)
    audible = peaks > threshold
    reference = float(np.median(peaks[audible])) if audible.any() else threshold
    gains = np.clip(reference - peaks, -6, 6)
    current, current_start, candidate, candidate_start = 0, 0, None, 0
    last_wide, wide_start = 0, None
    frames = []
    for index in range(levels.shape[1]):
        frame = index * step
        active = np.flatnonzero(levels[:, index] > threshold)
        silent = not len(active)
        if silent:
            wanted = current
        else:
            ordered = active[np.argsort((levels[:, index] + gains)[active])[::-1]]
            wanted = int(ordered[0])
            overlap = len(ordered) > 1 and float(levels[ordered[0], index] + gains[ordered[0]] -
                                                levels[ordered[1], index] - gains[ordered[1]]) < margin
            if wide and (overlap or (wide_every > 0 and frame - last_wide >= wide_every * fps)):
                wanted = -1
            if wide_start is not None and frame - wide_start < minimum_shot * fps:
                wanted = -1
        if index == 0 and not silent:
            current = wanted
            if current == -1:
                wide_start = 0
        if wanted != candidate:
            candidate, candidate_start = wanted, frame
        if wanted != current and frame - candidate_start >= reaction * fps and frame - current_start >= minimum_shot * fps:
            current, current_start = wanted, frame
            if current == -1:
                last_wide, wide_start = frame, frame
            else:
                wide_start = None
        label = {'start': frame, 'end': min(duration, frame + step), 'speaker': current, 'silent': silent}
        if frames and frames[-1]['speaker'] == current and frames[-1]['silent'] == silent:
            frames[-1]['end'] = label['end']
        else:
            frames.append(label)
    if not any(not p['silent'] for p in frames):
        raise ValueError('Nutq topilmadi. Mikrofon treklarini va ovoz chegarasini tekshiring.')
    return frames


def retained_ranges(plan: list[dict], duration: int, *, inside: int, outside: int,
                    remove_silence: bool, silence_frames: int, pad_frames: int) -> list[tuple[int, int]]:
    remove = []
    if remove_silence:
        run_start = None
        for item in [*plan, {'start': duration, 'end': duration, 'silent': False}]:
            if item['silent'] and run_start is None:
                run_start = item['start']
            elif not item['silent'] and run_start is not None:
                start, end = max(inside, run_start), min(outside, item['start'])
                if end - start >= silence_frames and start + pad_frames < end - pad_frames:
                    remove.append((start + pad_frames, end - pad_frames))
                run_start = None
    kept, position = [], 0
    for start, end in remove:
        if position < start:
            kept.append((position, start))
        position = end
    if position < duration:
        kept.append((position, duration))
    return kept


def make_schedule(timeline: Timeline, plan: list[dict], mappings: list[dict], *, wide_track: int | None,
                  inside: int, outside: int, remove_silence: bool, silence: float,
                  padding: float, switch_cameras: bool) -> list[dict]:
    fps = float(timeline.fps)
    kept = retained_ranges(plan, timeline.duration, inside=inside, outside=outside,
                           remove_silence=remove_silence, silence_frames=round(silence * fps),
                           pad_frames=round(padding * fps))
    edges = {inside, outside, *(p['start'] for p in plan), *(p['end'] for p in plan)}
    candidates = [m['video'] for m in mappings] + ([wide_track] if wide_track is not None else [])
    for index in candidates:
        for clip in timeline.video[index]:
            edges.update((clip.start, clip.end))
    schedule, output = [], 0
    for start, end in kept:
        boundaries = [start, *sorted(e for e in edges if start < e < end), end]
        for a, b in zip(boundaries, boundaries[1:]):
            camera = None
            if switch_cameras and inside <= a < outside:
                item = next(p for p in plan if p['start'] <= a < p['end'])
                desired = wide_track if item['speaker'] == -1 else mappings[item['speaker']]['video']
                available = [c for c in candidates if any(clip.enabled and clip.start <= a and clip.end >= b for clip in timeline.video[c])]
                if not available:
                    raise ValueError(f'{a / fps:.2f} soniyada kamera yo‘q. Kameralar uzunligini tekshiring.')
                camera = desired if desired in available else available[0]
            if schedule and schedule[-1]['end'] == a and schedule[-1]['camera'] == camera:
                schedule[-1]['end'] = b
            else:
                schedule.append({'start': a, 'end': b, 'output': output, 'camera': camera})
            output += b - a
    return schedule


def set_text(element: ET.Element, name: str, text: object) -> None:
    child = element.find(name)
    if child is None:
        child = ET.SubElement(element, name)
    child.text = str(text)


def center_crop(clip: ET.Element, width: int, height: int, fallback: tuple[int, int]) -> None:
    file = clip.find('file')
    source_width = int(file.findtext('media/video/samplecharacteristics/width', str(fallback[0])))
    source_height = int(file.findtext('media/video/samplecharacteristics/height', str(fallback[1])))
    if source_width <= 0 or source_height <= 0:
        raise ValueError('Media kadr o‘lchami noto‘g‘ri.')
    effect = next((e for e in clip.findall('filter/effect') if e.findtext('effectid') == 'basic'), None)
    if effect is None:
        effect = ET.SubElement(ET.SubElement(clip, 'filter'), 'effect')
        for name, value in [('name', 'Basic Motion'), ('effectid', 'basic'), ('effectcategory', 'motion'),
                            ('effecttype', 'motion'), ('mediatype', 'video')]:
            set_text(effect, name, value)
    for parameter in list(effect.findall('parameter')):
        if (parameter.findtext('parameterid') or parameter.get('parameterid')) in {'scale', 'center'}:
            effect.remove(parameter)
    parameter = ET.SubElement(effect, 'parameter')
    set_text(parameter, 'parameterid', 'scale')
    set_text(parameter, 'name', 'Scale')
    set_text(parameter, 'value', 100 * max(width / source_width, height / source_height))
    parameter = ET.SubElement(effect, 'parameter')
    set_text(parameter, 'parameterid', 'center')
    set_text(parameter, 'name', 'Center')
    value = ET.SubElement(parameter, 'value')
    set_text(value, 'horiz', 0)
    set_text(value, 'vert', 0)


def edit_xml(timeline: Timeline, schedule: list[dict], mapped_video: set[int], *,
             profile: str = 'original') -> ET.Element:
    sequence = copy.deepcopy(timeline.sequence)
    sequence.set('id', 'uzscribe-podcast-' + uuid.uuid4().hex)
    for uid in sequence.findall('uuid'):
        sequence.remove(uid)
    set_text(sequence, 'name', sequence.findtext('name', 'Podcast') + ' · UzScribe Podcast')
    set_text(sequence, 'duration', sum(s['end'] - s['start'] for s in schedule))
    def remap_frame(frame):
        for span in schedule:
            if frame < span['start']:
                return span['output']
            if frame <= span['end']:
                return span['output'] + frame - span['start']
        return sum(s['end'] - s['start'] for s in schedule)
    for marker in sequence.findall('marker'):
        for key in ('in', 'out'):
            value = int(marker.findtext(key, '-1'))
            if value >= 0:
                set_text(marker, key, remap_frame(value))
    for key in ('in', 'out'):
        if sequence.find(key) is not None:
            set_text(sequence, key, 0 if key == 'in' else sum(s['end'] - s['start'] for s in schedule))
    sizes = {'vertical': (1080, 1920), 'square': (1080, 1080), 'portrait': (1080, 1350), 'landscape': (1920, 1080)}
    characteristics = sequence.find('media/video/format/samplecharacteristics')
    fallback = (int(characteristics.findtext('width', '1920')), int(characteristics.findtext('height', '1080'))) if characteristics is not None else (1920, 1080)
    if profile != 'original':
        if profile not in sizes or characteristics is None:
            raise ValueError('Social kadr formati topilmadi.')
        width, height = sizes[profile]
        set_text(characteristics, 'width', width)
        set_text(characteristics, 'height', height)
        set_text(characteristics, 'pixelaspectratio', 'square')
    records, seen_files = [], set()
    for kind, original_tracks in [('video', timeline.video), ('audio', timeline.audio)]:
        for track_index, track in enumerate(sequence.findall('media/' + kind + '/track')):
            first_clip = track.find('clipitem')
            insert_at = list(track).index(first_clip) if first_clip is not None else 0
            transitions = list(track.findall('transitionitem'))
            for item in list(track.findall('clipitem')) + transitions:
                track.remove(item)
            for source in original_tracks[track_index]:
                for span in schedule:
                    if source.enabled and kind == 'video' and track_index in mapped_video and span['camera'] is not None and span['camera'] != track_index:
                        continue
                    start, end = max(source.start, span['start']), min(source.end, span['end'])
                    if start >= end:
                        continue
                    clip = copy.deepcopy(source.element)
                    inside = min(source.outside - 1, source.inside + round(Fraction(start - source.start, 1) * source.fps / timeline.fps))
                    outside = min(source.outside, max(inside + 1, source.inside + round(Fraction(end - source.start, 1) * source.fps / timeline.fps)))
                    output_start = span['output'] + start - span['start']
                    for key, value in [('start', output_start), ('end', output_start + end - start), ('in', inside), ('out', outside)]:
                        set_text(clip, key, value)
                    for key, value in [('pproTicksIn', inside), ('pproTicksOut', outside)]:
                        if clip.find(key) is not None:
                            set_text(clip, key, round(Fraction(value * 254016000000, 1) / source.fps))
                    for item in list(clip.findall('link')) + list(clip.findall('masterclipid')):
                        clip.remove(item)
                    file = clip.find('file')
                    file_position = list(clip).index(file)
                    clip.remove(file)
                    resolved = copy.deepcopy(source.file)
                    file_id = resolved.get('id') or 'uzscribe-file-' + uuid.uuid5(uuid.NAMESPACE_URL, str(source.path)).hex
                    resolved.set('id', file_id)
                    clip.insert(file_position, resolved)
                    if profile != 'original' and kind == 'video':
                        center_crop(clip, width, height, fallback)
                    if file_id in seen_files:
                        clip.remove(resolved)
                        clip.insert(file_position, ET.Element('file', id=file_id))
                    seen_files.add(file_id)
                    clip.set('id', 'uzscribe-clip-' + str(len(records) + 1))
                    track.insert(insert_at, clip)
                    insert_at += 1
                    records.append((clip, kind, track_index + 1, len(track.findall('clipitem')),
                                    (file_id, inside, outside, output_start, end - start)))
            for original_transition in transitions:
                a, b = int(original_transition.findtext('start', '-1')), int(original_transition.findtext('end', '-1'))
                span = next((s for s in schedule if s['start'] <= a < b <= s['end']), None)
                if span is None:
                    continue
                transition = copy.deepcopy(original_transition)
                start, end = span['output'] + a - span['start'], span['output'] + b - span['start']
                set_text(transition, 'start', start); set_text(transition, 'end', end)
                alignment = transition.findtext('alignment', '')
                before = next((c for c in track.findall('clipitem') if int(c.findtext('end')) == end), None)
                after = next((c for c in track.findall('clipitem') if int(c.findtext('start')) == start), None)
                if alignment == 'end-black' and before is None or alignment == 'start-black' and after is None:
                    continue
                if alignment not in {'end-black', 'start-black'} and (before is None or after is None):
                    continue
                if before is not None and alignment != 'start-black':
                    set_text(before, 'end', -1)
                if after is not None and alignment != 'end-black':
                    set_text(after, 'start', -1)
                position = list(track).index(before) + 1 if before is not None and alignment != 'start-black' else list(track).index(after)
                track.insert(position, transition)
    groups = {}
    for record in records:
        groups.setdefault(record[-1], []).append(record)
    for clip, kind, track_index, clip_index, signature in records:
        for linked, linked_kind, linked_track, linked_index, _ in groups[signature]:
            link = ET.SubElement(clip, 'link')
            for name, value in [('linkclipref', linked.get('id')), ('mediatype', linked_kind),
                                ('trackindex', linked_track), ('clipindex', linked_index)]:
                set_text(link, name, value)
    root = ET.Element('xmeml', version='5')
    root.append(sequence)
    return root


def run(source: Path, output: Path, settings: dict, *, vad: bool = True) -> dict:
    timeline = parse_timeline(source)
    mappings = settings.get('speakers', [])
    if not 1 <= len(mappings) <= 10:
        raise ValueError('1–10 ta mikrofon–kamera mosligini kiriting.')
    switch = bool(settings.get('switch_cameras', True))
    if len({m['audio'] for m in mappings}) != len(mappings):
        raise ValueError('Har odam uchun alohida mikrofon treki tanlang. Umumiy audio uchun faqat pauza rejimidan foydalaning.')
    for mapping in mappings:
        if not isinstance(mapping.get('audio'), int) or not 0 <= mapping['audio'] < len(timeline.audio):
            raise ValueError('Audio trek mosligi noto‘g‘ri.')
        if not isinstance(mapping.get('video'), int) or not 0 <= mapping['video'] < len(timeline.video):
            raise ValueError('Kamera trek mosligi noto‘g‘ri.')
    wide = settings.get('wide_track')
    if wide is not None and (not isinstance(wide, int) or not 0 <= wide < len(timeline.video)):
        raise ValueError('Umumiy kamera treki topilmadi.')
    if wide is not None and wide in {m['video'] for m in mappings}:
        raise ValueError('Umumiy kamera uchun alohida video trek tanlang.')
    def number(key, default, low, high):
        value = float(settings.get(key, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} sozlamasini tekshiring ({low}–{high}).')
        return value
    fps = float(timeline.fps)
    inside = round(number('start', 0, 0, timeline.duration / fps) * fps)
    outside = round(number('end', timeline.duration / fps, 0, timeline.duration / fps) * fps)
    if inside >= outside:
        raise ValueError('In/Out oralig‘i noto‘g‘ri.')
    minimum_shot = number('minimum_shot', 2.5, 0.5, 30)
    reaction = number('reaction', .35, .1, 3)
    threshold = number('threshold', -42, -80, -10)
    margin = number('margin', 3, 0, 20)
    silence = number('silence', 1, .3, 10)
    padding = number('padding', .2, 0, 1)
    wide_every = number('wide_every', 30, 0, 300)
    step = max(1, round(fps / 10))
    activity = []; warnings = []; mappings = [dict(m) for m in mappings]
    for index, mapping in enumerate(mappings, 1):
        print(f'UZPOD {index}/{len(mappings)} Mikrofon {mapping["audio"] + 1}', flush=True)
        actual, detected, warning = speech_activity(timeline, mapping['audio'], step, inside, outside, threshold, vad=vad, allow_sibling=len(mappings)==1)
        mapping['audio'] = actual
        activity.append(detected)
        if warning: warnings.append(warning)
    levels = np.stack(activity)
    # Activity outside the selected range cannot make an empty selected range pass.
    if not np.any(levels[:, inside // step:math.ceil(outside / step)] > threshold):
        raise ValueError('Tanlangan mikrofonlarda In/Out qismida nutq yo‘q. Nutq bor audio trekni tanlang; chap/o‘ng kanal va trekning mute holatini tekshiring.')
    plan = camera_plan(levels, step=step, duration=timeline.duration, fps=fps,
                       threshold=threshold, minimum_shot=minimum_shot, reaction=reaction,
                       margin=margin, wide=wide is not None, wide_every=wide_every)
    schedule = make_schedule(timeline, plan, mappings, wide_track=wide, inside=inside, outside=outside,
                             remove_silence=bool(settings.get('remove_silence', True)), silence=silence,
                             padding=padding, switch_cameras=switch)
    mapped_video = {m['video'] for m in mappings} | ({wide} if wide is not None else set())
    result = edit_xml(timeline, schedule, mapped_video, profile=settings.get('profile', 'original'))
    total = sum(s['end'] - s['start'] for s in schedule)
    report = {'schema': 1, 'warnings': warnings, 'speakers': mappings, 'source': str(source), 'xml': str(output), 'fps': fps,
              'original_frames': timeline.duration, 'output_frames': total,
              'removed_seconds': (timeline.duration - total) / fps,
              'output_seconds': total / fps, 'cuts': schedule,
              'speakers': mappings, 'profile': settings.get('profile', 'original')}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp.xml')
    ET.ElementTree(result).write(temporary, encoding='utf-8', xml_declaration=True)
    temporary.replace(output)
    output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='UzScribe Podcast montaji')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--settings', required=True, type=Path)
    parser.add_argument('--no-vad', action='store_true', help='Diagnostika: faqat audio ovozini o‘lchash')
    args = parser.parse_args()
    try:
        run(args.input, args.output, json.loads(args.settings.read_text(encoding='utf-8')), vad=not args.no_vad)
    except (OSError, ValueError, ET.ParseError, KeyError, ImportError, subprocess.SubprocessError) as exc:
        print(f'Podcast montaji tugamadi: {exc}', file=sys.stderr)
        return 1
    print('UzScribe Podcast montaji tayyor.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
