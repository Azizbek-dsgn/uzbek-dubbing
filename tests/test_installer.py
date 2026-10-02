import json
import ast
import tempfile
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from install import destinations, install
from install_online import (CONVERT, DOWNLOAD_GIGAAM, _navai_ready,
                            _prepare_environment, _install_gigaam,
                            _verify_installation, VERIFY_RUNTIME, _retry_download)


class InstallerTests(unittest.TestCase):
    def test_platform_destinations(self):
        home = Path('/testhome')
        runtime, panel = destinations('darwin', home, {})
        self.assertEqual(runtime, home / 'Library/Application Support/UzbekSubtitles')
        self.assertEqual(panel, home / 'Library/Application Support/Adobe/CEP/extensions/UzbekSubtitles')
        runtime, panel = destinations('win32', home,
                                      {'LOCALAPPDATA': '/local', 'APPDATA': '/roaming'})
        self.assertEqual(runtime, Path('/local/UzbekSubtitles'))
        self.assertEqual(panel, Path('/roaming/Adobe/CEP/extensions/UzbekSubtitles'))

    def test_staged_runtime_and_panel_without_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            package = base / 'package'
            (package / 'subtitles').mkdir(parents=True)
            (package / 'subtitles/cli.py').write_text('print("ok")')
            (package / 'models/large-v3').mkdir(parents=True)
            (package / 'models/large-v3/model.bin').write_bytes(b'test')
            (package / 'adobe/UzbekSubtitles/CSXS').mkdir(parents=True)
            (package / 'adobe/UzbekSubtitles/host').mkdir()
            (package / 'adobe/UzbekSubtitles/assets').mkdir()
            (package / 'adobe/UzbekSubtitles/assets/uzscribe-logo.jpg').write_bytes(b'logo')
            (package / 'adobe/UzbekSubtitles/CSXS/manifest.xml').write_text('<root/>')
            for name in ('index.html', 'panel.js', 'animation-panel.js', 'podcast-panel.js', 'reels-panel.js'):
                (package / 'adobe/UzbekSubtitles' / name).write_text(name)
            (package / 'adobe/UzbekSubtitles/host/editor.jsx').write_text('editor')
            with patch('install._enable_debug') as debug:
                runtime, panel = install(package, 'darwin', base / 'home', {},
                                         developer=True, skip_dependencies=True)
            self.assertEqual((runtime / 'models/large-v3/model.bin').read_bytes(), b'test')
            self.assertEqual((panel / 'panel.js').read_text(), 'panel.js')
            self.assertEqual((panel / 'assets/uzscribe-logo.jpg').read_bytes(), b'logo')
            debug.assert_called_once_with('darwin')
            with patch('install._enable_debug'):
                install(package, 'darwin', base / 'home', {}, developer=True,
                        skip_dependencies=True, model_source=runtime / 'models/large-v3')
            self.assertEqual((runtime / 'models/large-v3/model.bin').read_bytes(), b'test')

    def test_online_converter_script_is_valid_python(self):
        ast.parse(CONVERT)
        ast.parse(DOWNLOAD_GIGAAM)
        ast.parse(VERIFY_RUNTIME)

    def test_incomplete_navai_install_is_not_treated_as_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp)
            (model / 'model.bin').write_bytes(b'partial')
            self.assertFalse(_navai_ready(model))
            (model / 'config.json').write_text('{}')
            (model / 'tokenizer.json').write_text('{}')
            self.assertFalse(_navai_ready(model))
            with (model / 'model.bin').open('wb') as output:
                output.truncate(100_000_000)
            self.assertTrue(_navai_ready(model))

    def test_uv_installs_into_windows_runtime_when_bootstrap_provides_it(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            python = runtime / '.venv/Scripts/python.exe'
            python.parent.mkdir(parents=True)
            python.touch()
            with patch('install_online.subprocess.run') as run:
                run.return_value.returncode = 0
                result = _prepare_environment(runtime, 'win32', convert=True,
                                              uv=Path('C:/uv/uv.exe'))
            self.assertEqual(result, python)
            self.assertEqual(run.call_count, 3)
            for call in run.call_args_list[1:]:
                self.assertEqual(call.args[0][:5],
                                 [str(Path('C:/uv/uv.exe')), 'pip', 'install',
                                  '--python', str(python)])

    def test_gigaam_installer_uses_uv_and_downloads_into_runtime(self):
        runtime = Path('C:/Users/Test/AppData/Local/UzbekSubtitles')
        python = runtime / '.venv/Scripts/python.exe'
        with patch('install_online.subprocess.run') as run, \
             patch('install_online._intel_mac', return_value=False):
            _install_gigaam(runtime, python, Path('C:/uv/uv.exe'))
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args_list[0].args[0][:5],
                         [str(Path('C:/uv/uv.exe')), 'pip', 'install',
                          '--python', str(python)])
        self.assertIn('requirements-gigaam.txt', run.call_args_list[0].args[0][-2])
        self.assertEqual(run.call_args_list[2].args[0][-1], str(runtime))

    def test_fresh_runtime_uses_uv_venv_without_system_pip(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'new-runtime'
            with patch('install_online.subprocess.run') as run:
                python = _prepare_environment(runtime, 'win32', convert=False,
                                              uv=Path('C:/uv/uv.exe'))
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][:3],
                             [str(Path('C:/uv/uv.exe')), 'venv', '--python'])
            self.assertEqual(run.call_args_list[0].args[0][-1], str(runtime / '.venv'))
            self.assertEqual(run.call_args_list[1].args[0][:5],
                             [str(Path('C:/uv/uv.exe')), 'pip', 'install', '--python', str(python)])

    def test_intel_mac_uses_compatible_dependencies_for_conversion_too(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch('install_online.platform.machine', return_value='x86_64'), \
             patch('install_online.subprocess.run') as run:
            _prepare_environment(Path(temp), 'darwin', convert=True, uv=Path('uv'))
            self.assertEqual(run.call_count, 2)
            self.assertTrue(run.call_args_list[1].args[0][-1].endswith('requirements-intel-mac.txt'))

    def test_broken_python_is_preserved_and_environment_recreated(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            python = runtime / '.venv/Scripts/python.exe'
            python.parent.mkdir(parents=True)
            python.write_bytes(b'broken')
            with patch('install_online.subprocess.run') as run:
                run.return_value.returncode = 1
                _prepare_environment(runtime, 'win32', convert=False, uv=Path('uv.exe'))
            backup = list(runtime.glob('.venv-backup-*'))
            self.assertEqual(len(backup), 1)
            self.assertEqual((backup[0] / 'Scripts/python.exe').read_bytes(), b'broken')
            self.assertEqual(run.call_args_list[1].args[0][1], 'venv')

    def test_interrupted_download_retries_and_persistent_failure_is_reported(self):
        failure = subprocess.CalledProcessError(1, ['download'])
        with patch('install_online.subprocess.run', side_effect=[failure, None]) as run, \
             patch('install_online.time.sleep'):
            _retry_download(['download'])
            self.assertEqual(run.call_count, 2)
        with patch('install_online.subprocess.run', side_effect=failure) as run, \
             patch('install_online.time.sleep'):
            with self.assertRaises(subprocess.CalledProcessError):
                _retry_download(['download'])
            self.assertEqual(run.call_count, 3)

    def test_post_install_check_requires_both_models_and_panel(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'runtime'
            panel = Path(temp) / 'panel'
            python = runtime / '.venv/Scripts/python.exe'
            files = [python,
                     *(runtime / 'models/large-v3' / name for name in
                       ('model.bin', 'config.json', 'tokenizer.json')),
                     *(runtime / 'models/gigaam-base-large' / name for name in
                       ('config.json', 'modeling_gigaam.py')),
                     *(panel / name for name in
                       ('CSXS/manifest.xml', 'index.html', 'panel.js', 'animation-panel.js', 'podcast-panel.js', 'reels-panel.js',
                        'assets/uzscribe-logo.jpg'))]
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with (runtime / 'models/large-v3/model.bin').open('wb') as output:
                output.truncate(100_000_000)
            checkpoint = (runtime / 'models/gigaam-uzbek/checkpoints/'
                          'large_full_600m/best.pt')
            checkpoint.parent.mkdir(parents=True)
            with checkpoint.open('wb') as output:
                output.truncate(100_000_001)
            _verify_installation(runtime, panel, python)
            (panel / 'panel.js').unlink()
            with self.assertRaisesRegex(RuntimeError, 'panel.js'):
                _verify_installation(runtime, panel, python)

    def test_manifest_targets_adobe_2020_hosts_and_cep9(self):
        manifest = ET.parse(Path(__file__).resolve().parents[1] /
                            'adobe/UzbekSubtitles/CSXS/manifest.xml').getroot()
        hosts = {host.attrib['Name']: host.attrib['Version']
                 for host in manifest.findall('./ExecutionEnvironment/HostList/Host')}
        self.assertEqual(hosts['PPRO'], '[14.0,99.9]')
        self.assertEqual(hosts['AEFT'], '[17.0,99.9]')
        runtime = manifest.find('./ExecutionEnvironment/RequiredRuntimeList/RequiredRuntime')
        self.assertEqual(runtime.attrib['Version'], '9.0')

    def test_checksum_rejects_corrupt_package(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / 'checksums.json').write_text(json.dumps({'subtitles/cli.py': 'bad'}))
            with self.assertRaisesRegex(RuntimeError, 'buzilgan'):
                install(base, 'win32', base / 'home', {}, developer=False,
                        skip_dependencies=True)


if __name__ == '__main__':
    unittest.main()
