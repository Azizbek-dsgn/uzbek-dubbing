import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subtitles.model_assets import fetch, require_features, SPEAKER_ASSETS

class FeatureAssetTests(unittest.TestCase):
    def test_atomic_download_checksum_and_cached_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'model.onnx';file.write_bytes(b'old')
            digest=hashlib.sha256(b'valid model').hexdigest()
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'broken')):
                with self.assertRaisesRegex(RuntimeError,'tekshiruvdan'):fetch('https://example.com/model',file,digest)
            self.assertEqual(file.read_bytes(),b'old');self.assertFalse(file.with_suffix('.onnx.part').exists())
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'valid model')):fetch('https://example.com/model',file,digest)
            self.assertEqual(file.read_bytes(),b'valid model')
            with patch('urllib.request.urlopen') as download:
                fetch('https://example.com/model',file,digest);download.assert_not_called()

    def test_completion_requires_every_feature_model(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp)
            with self.assertRaisesRegex(RuntimeError,'Scribe Nav'):require_features(runtime)
            nav=runtime/'models/navai-medium';nav.mkdir(parents=True)
            for name in ('config.json','tokenizer.json','preprocessor_config.json'): (nav/name).touch()
            with (nav/'model.bin').open('wb') as output:output.truncate(100_000_000)
            with self.assertRaisesRegex(RuntimeError,'Matnni'):require_features(runtime)
            correct=runtime/'models/rubai-transcript';correct.mkdir()
            for name in ('config.json','tokenizer_config.json'):(correct/name).touch()
            with (correct/'model.safetensors').open('wb') as output:output.truncate(100_000_000)
            speaker=runtime/'models/speaker-onnx';speaker.mkdir()
            for name in SPEAKER_ASSETS:(speaker/name).touch()
            hashes={speaker/name:digest for name,(_,digest) in SPEAKER_ASSETS.items()}
            with patch('subtitles.model_assets.checksum',side_effect=lambda p:hashes[p]):require_features(runtime)
            (speaker/'embedding.onnx').unlink()
            with patch('subtitles.model_assets.checksum',side_effect=lambda p:hashes[p]),self.assertRaisesRegex(RuntimeError,'embedding.onnx'):require_features(runtime)
