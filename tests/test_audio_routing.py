import copy
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from test_podcast import fixture
from subtitles.podcast import audio_route, parse_timeline, speech_activity, track_activity
from subtitles.reels import render_audio


class AudioRoutingTests(unittest.TestCase):
    def test_premiere_split_mono_stereo_uses_right_channel_in_both_engines(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); source = folder / 'source.xml'
            root = fixture(source, duration=50, microphones=1)
            for clip in root.findall('.//clipitem'):
                clip.find('in').text = '0'; clip.find('out').text = '50'
                file = clip.find('file'); audio = file.find('media/audio')
                channel = ET.SubElement(audio, 'audiochannel')
                ET.SubElement(channel, 'sourcechannel').text = '1'
                right = copy.deepcopy(audio); right.find('audiochannel/sourcechannel').text = '2'
                file.find('media').append(right)
            audio_stream = root.find('sequence/media/audio')
            right_track = copy.deepcopy(audio_stream.find('track'))
            right_track.find('clipitem').set('id', 'right-audio')
            right_track.find('clipitem/sourcetrack/trackindex').text = '2'
            audio_stream.append(right_track); ET.ElementTree(root).write(source)
            samples = np.zeros((32000, 2), dtype='<i2')
            samples[:, 1] = (4000 * np.sin(2*np.pi*220*np.arange(32000)/16000)).astype('<i2')
            with wave.open(str(folder/'media 0.wav'), 'wb') as wav:
                wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(16000)
                wav.writeframes(samples.tobytes())
            timeline = parse_timeline(source)
            self.assertEqual(audio_route(timeline.audio[1][0]), (0, 1))
            self.assertTrue(np.all(track_activity(timeline, 0, 3, vad=False) <= -99))
            self.assertGreater(track_activity(timeline, 1, 3, vad=False).max(), -30)
            selected, levels, warning = speech_activity(timeline, 0, 3, 0, 50, -42, vad=False)
            self.assertEqual(selected, 1); self.assertIn('Audio 2', warning)
            out = folder/'right.wav'; render_audio(timeline, 1, 0, 50, out)
            with wave.open(str(out)) as wav:
                decoded = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')
                self.assertGreater(np.abs(decoded).max(), 3000)
            timeline.audio[1][0].channel = 2
            with self.assertRaisesRegex(ValueError, 'kanali 3 topilmadi'):
                audio_route(timeline.audio[1][0])

    def test_silent_input_never_falls_back_to_unrelated_music_or_microphone(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'source.xml'; fixture(source)
            timeline = parse_timeline(source)
            with patch('subtitles.podcast.track_activity', return_value=np.full(100, -100.)) as read:
                actual, _, warning = speech_activity(timeline, 0, 3, 0, 300, -42)
                self.assertEqual(actual, 0); self.assertEqual(warning, '')
                self.assertEqual(read.call_count, 1)
