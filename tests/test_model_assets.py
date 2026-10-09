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

    def test_nav_conversion_failure_preserves_download_and_success_moves_model(self):
        from types import SimpleNamespace
        import errno
        from subtitles.model_assets import install_features
        from subtitles.install_storage import navai_download_dir
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp);calls=[];fail=[True]
            old=runtime/'models/navai-medium';old.mkdir(parents=True)
            (old/'model.bin').write_bytes(b'old incomplete')
            def snapshot(repo, local_dir, **kwargs):
                folder=Path(local_dir);folder.mkdir(parents=True,exist_ok=True)
                if repo.startswith('navai') and '*.safetensors' in kwargs['allow_patterns']:
                    weight=folder/'model.safetensors'
                    if not weight.exists():weight.write_bytes(b'original weight');calls.append('download')
            def convert(output, **kwargs):
                if fail[0]:raise OSError(errno.ENOSPC,'no space')
                folder=Path(output);folder.mkdir()
                for name in ['config.json','tokenizer.json','preprocessor_config.json']:(folder/name).touch()
                with (folder/'model.bin').open('wb') as f:f.truncate(100_000_000)
            tokenizer=SimpleNamespace(from_pretrained=lambda *a,**k:SimpleNamespace(save_pretrained=lambda *a:None))
            converter=lambda *a,**k:SimpleNamespace(convert=convert)
            with patch.dict('sys.modules', {
                'huggingface_hub':SimpleNamespace(snapshot_download=snapshot),
                'transformers':SimpleNamespace(AutoTokenizer=tokenizer),
                'ctranslate2.converters':SimpleNamespace(TransformersConverter=converter)}), \
                 patch('subtitles.model_assets.fetch'), patch('subtitles.model_assets.require_space'), \
                 patch('subtitles.model_assets.require_features'), patch('subtitles.model_assets.shutil.copy2') as copy:
                with self.assertRaises(OSError):install_features(runtime)
                self.assertEqual((navai_download_dir(runtime)/'model.safetensors').read_bytes(), b'original weight')
                self.assertEqual((old/'model.bin').read_bytes(),b'old incomplete')
                self.assertEqual(list(runtime.glob('uzscribe-navai-*')), [])
                fail[0]=False
                replace=Path.replace
                def fail_swap(path, target):
                    if path.name=='converted':raise OSError(errno.ENOSPC,'no space')
                    return replace(path,target)
                with patch.object(Path,'replace',fail_swap):
                    with self.assertRaises(OSError):install_features(runtime)
                self.assertEqual((old/'model.bin').read_bytes(),b'old incomplete')
                self.assertTrue((navai_download_dir(runtime)/'model.safetensors').is_file())
                install_features(runtime)
                self.assertEqual(calls,['download'])
                self.assertFalse(navai_download_dir(runtime).exists())
                self.assertEqual((old/'model.bin').stat().st_size,100_000_000)
                self.assertFalse(any(Path(c.args[0]).name=='model.bin' for c in copy.call_args_list))
