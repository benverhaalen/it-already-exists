"""Synthetic archive mechanics only; no real APK or reconstructed product."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

MODULE = Path(__file__).resolve().parents[1] / 'tools/inspect_apk_reference.py'
spec = importlib.util.spec_from_file_location('apk_intake', MODULE)
apk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apk)


class IntakeTests(unittest.TestCase):
    def test_mixed_payload_preserves_alternatives_and_caps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mixed.apk'
            with zipfile.ZipFile(path, 'w') as archive:
                for name in ['AndroidManifest.xml', 'classes.dex', 'lib/arm64-v8a/libflutter.so',
                             'lib/arm64-v8a/libunity.so', 'assets/index.android.bundle',
                             'assets/flutter_assets/a', '../bad', 'split_config.en.apk']:
                    archive.writestr(name, b'not real payload')
            result = apk.inspect(path, 1)
            self.assertTrue(result['inventory']['truncated'])
            self.assertEqual(len(result['framework_hypotheses']), 3)
            self.assertEqual(result['native_abis'], ['arm64-v8a'])
            methods = {r['method_id'] for r in result['next_inspection']}
            self.assertTrue({'dex-recovery', 'dart-aot', 'unity-layer-recovery', 'hermes-tables'} <= methods)
            self.assertEqual(result['bounds']['decoded_payload_bytes'], 0)
            self.assertEqual(result['package']['split_indicators']['total'], 1)
            self.assertEqual(result['reference_id'], apk.inspect(path)['reference_id'])
            self.assertTrue(any(i['unsafe_path'] for i in apk.inspect(path)['inventory']['items']))

    def test_malformed_and_oversized_directory_block_before_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.apk'
            path.write_bytes(b'not a ZIP')
            with self.assertRaises(apk.IntakeError):
                apk.inspect(path)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('a', b'')
            data = bytearray(path.read_bytes())
            end = data.rfind(b'PK\x05\x06')
            data[end + 12:end + 16] = (apk.MAX_DIRECTORY + 1).to_bytes(4, 'little')
            path.write_bytes(data)
            with self.assertRaisesRegex(apk.IntakeError, 'exceeds intake bounds'):
                apk.inspect(path)

    def test_no_framework_or_installability_claim_from_empty_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'empty.apk'
            with zipfile.ZipFile(path, 'w'):
                pass
            result = apk.inspect(path)
            self.assertEqual(result['framework_hypotheses'], [])
            self.assertIn('unknown', result['package']['split_status'])
            self.assertFalse(result['package']['manifest_entry_present'])
            self.assertEqual(result['package']['signature_status'].split(';')[0], 'not verified')


if __name__ == '__main__':
    unittest.main()
