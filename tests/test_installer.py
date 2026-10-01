import json
import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from install import destinations, install
from install_online import CONVERT


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
            (package / 'models/navai-small').mkdir(parents=True)
            (package / 'models/navai-small/model.bin').write_bytes(b'test')
            (package / 'adobe/UzbekSubtitles/CSXS').mkdir(parents=True)
            (package / 'adobe/UzbekSubtitles/host').mkdir()
            (package / 'adobe/UzbekSubtitles/CSXS/manifest.xml').write_text('<root/>')
            for name in ('index.html', 'panel.js'):
                (package / 'adobe/UzbekSubtitles' / name).write_text(name)
            (package / 'adobe/UzbekSubtitles/host/editor.jsx').write_text('editor')
            with patch('install._enable_debug') as debug:
                runtime, panel = install(package, 'darwin', base / 'home', {},
                                         developer=True, skip_dependencies=True)
            self.assertEqual((runtime / 'models/navai-small/model.bin').read_bytes(), b'test')
            self.assertEqual((panel / 'panel.js').read_text(), 'panel.js')
            debug.assert_called_once_with('darwin')
            with patch('install._enable_debug'):
                install(package, 'darwin', base / 'home', {}, developer=True,
                        skip_dependencies=True, model_source=runtime / 'models/navai-small')
            self.assertEqual((runtime / 'models/navai-small/model.bin').read_bytes(), b'test')

    def test_online_converter_script_is_valid_python(self):
        ast.parse(CONVERT)

    def test_checksum_rejects_corrupt_package(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / 'checksums.json').write_text(json.dumps({'subtitles/cli.py': 'bad'}))
            with self.assertRaisesRegex(RuntimeError, 'buzilgan'):
                install(base, 'win32', base / 'home', {}, developer=False,
                        skip_dependencies=True)


if __name__ == '__main__':
    unittest.main()
