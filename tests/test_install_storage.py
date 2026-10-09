import errno
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from subtitles.install_storage import (GIB, SPACE_EXIT, InsufficientSpace,
    installation_budget, is_disk_full, navai_download_budget, navai_download_dir,
    require_space)
from install_online import _retry_download, main, CONVERT, DOWNLOAD_GIGAAM


class StorageTests(unittest.TestCase):
    def test_preflight_reports_target_free_and_required_space(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'missing/runtime'
            with patch('subtitles.install_storage.shutil.disk_usage', return_value=SimpleNamespace(free=GIB)) as usage:
                with self.assertRaisesRegex(InsufficientSpace, 'bo‘sh 1.0 GiB, kerak kamida 3.0 GiB'):
                    require_space(target, 3*GIB, 'Scribe Nav')
                self.assertEqual(usage.call_args.args[0], Path(temp).resolve())
            self.assertFalse(target.exists())

    def test_fresh_install_checks_space_before_any_dependency_work(self):
        with tempfile.TemporaryDirectory() as temp, patch('sys.argv', ['install_online.py']), \
             patch('install_online.destinations', return_value=(Path(temp)/'runtime', Path(temp)/'panel')), \
             patch('subtitles.install_storage.shutil.disk_usage', return_value=SimpleNamespace(free=GIB)), \
             patch('install_online._prepare_environment') as prepare:
            self.assertEqual(main(), SPACE_EXIT)
            prepare.assert_not_called()

    def test_disk_full_is_not_retried_and_wrapped_windows_errors_are_recognized(self):
        with patch('install_online.subprocess.run', side_effect=subprocess.CalledProcessError(SPACE_EXIT, ['download'])) as run, \
             patch('install_online.time.sleep') as sleep:
            with self.assertRaises(InsufficientSpace):_retry_download(['download'])
            self.assertEqual(run.call_count, 1);sleep.assert_not_called()
        error = OSError('disk full');error.winerror = 112
        wrapped = RuntimeError('download failed');wrapped.__cause__ = error
        self.assertTrue(is_disk_full(wrapped))
        self.assertFalse(is_disk_full(OSError(errno.EACCES, 'permission denied')))

    def test_download_worker_exits_28_for_real_and_wrapped_enospc(self):
        root = Path(__file__).resolve().parents[1]
        for wrapped in [False, True]:
            code = 'from subtitles.install_storage import install_error_hook\nimport errno\ninstall_error_hook()\n'
            if wrapped:
                code += 'try:\n raise OSError(errno.ENOSPC,"no space")\nexcept OSError as e:\n raise RuntimeError("download") from e\n'
            else:code += 'raise OSError(errno.ENOSPC,"no space")\n'
            result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True,
                                    env={**os.environ, 'PYTHONUTF8':'1'})
            self.assertEqual(result.returncode, SPACE_EXIT, result.stderr)
            self.assertIn('Diskda joy tugadi', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        self.assertIn('install_error_hook()', CONVERT)
        self.assertIn('install_error_hook()', DOWNLOAD_GIGAAM)

    def test_budget_reuses_finished_nav_weights_and_installed_models(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp)
            fresh=installation_budget(runtime)
            self.assertGreater(fresh, 20*GIB)
            cache=navai_download_dir(runtime);cache.mkdir(parents=True)
            with (cache/'model.safetensors').open('wb') as f:f.truncate(3*GIB)
            with (cache/'download.incomplete').open('wb') as f:f.truncate(5*GIB)
            self.assertAlmostEqual(navai_download_budget(runtime)/GIB, 1.7)
            (runtime/'.venv').mkdir()
            for name in ['navai-medium/model.bin','rubai-transcript/model.safetensors',
                         'gigaam-uzbek/checkpoints/large_full_600m/best.pt']:
                path=runtime/'models'/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('wb') as f:f.truncate(100_000_000)
            for name in ['config.json','tokenizer.json','preprocessor_config.json']:
                (runtime/'models/navai-medium'/name).touch()
            self.assertLess(installation_budget(runtime,global_ready=True), 4*GIB)

    def test_global_download_uses_target_volume_and_survives_interruption(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp)/'runtime'
            def interrupted(command):
                download=Path(command[-1])/'converted'
                download.mkdir(parents=True,exist_ok=True)
                (download/'partial.incomplete').write_bytes(b'resume me')
                raise InsufficientSpace('disk full')
            with patch('sys.argv',['install_online.py']), \
                 patch('install_online.destinations',return_value=(runtime,Path(temp)/'panel')), \
                 patch('install_online.require_space'), \
                 patch('install_online._prepare_environment',return_value=runtime/'.venv/bin/python'), \
                 patch('install_online._retry_download',side_effect=interrupted), \
                 patch('install_online.install') as install:
                self.assertEqual(main(),SPACE_EXIT)
                install.assert_not_called()
                caches=list((runtime/'models/.downloads').glob('global-*/converted/partial.incomplete'))
                self.assertEqual(len(caches),1)
                self.assertEqual(caches[0].read_bytes(),b'resume me')

    def test_windows_bootstrap_is_ascii_for_powershell_51(self):
        source=(Path(__file__).resolve().parents[1]/'bootstrap-windows.ps1').read_text()
        self.assertTrue(source.isascii())
        self.assertIn('AvailableFreeSpace',source)
        self.assertIn('$LASTEXITCODE -eq 28',source)
        # Uzbek apostrophes inside double quoted messages remain literal.
        for line in source.splitlines():
            if "o'rnat" in line or "bo'sh" in line:
                self.assertIn('"',line)
