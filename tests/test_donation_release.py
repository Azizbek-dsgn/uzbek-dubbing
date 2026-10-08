import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from tools import build_release


class DonationReleaseTests(unittest.TestCase):
    def test_free_release_has_qr_and_no_subscription_client(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);model=folder/'model';model.mkdir()
            for name in build_release.MODEL:(model/name).write_bytes(b'packaging fixture')
            target=folder/'plugin.zip';build_release.build(model,target)
            with zipfile.ZipFile(target) as archive:
                checksums=json.loads(archive.read('checksums.json'))
                for name in ['donation-panel.js','assets/donation-qr.svg']:
                    key='adobe/UzbekSubtitles/'+name
                    self.assertEqual(hashlib.sha256(archive.read(key)).hexdigest(),checksums[key])
                for name in ['license-panel.js','license-config.json','license-core.js']:
                    self.assertNotIn('adobe/UzbekSubtitles/'+name,archive.namelist())
                self.assertFalse(any(n.startswith('billing/') for n in archive.namelist()))

    def test_obsolete_subscription_config_cannot_reenable_paywall(self):
        with self.assertRaisesRegex(ValueError,'Obuna distributivi olib tashlangan'):
            build_release.build(Path('model'),Path('plugin.zip'),license_config=Path('old.json'))
