"""Comparison classifications must not conflate runtime compatibility with
application equivalence."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apk_native_compare as compare_mod
from test_apk_native_profile import elf
import apk_native_profile as profile


def write_apk(path, entries):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in entries.items():
            z.writestr(name, data)


class NativeCompareTests(unittest.TestCase):
    def test_missing_digest_cannot_produce_identity(self):
        incomplete = {"schema_version": 1, "input": {"sha256": None}, "libraries": []}
        with self.assertRaisesRegex(ValueError, "SHA256"):
            compare_mod.compare(incomplete, incomplete)

    def test_identical_bytes_across_two_apks(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            write_apk(b, {'lib/arm64-v8a/libapp.so': elf(64, 183), 'README': b'distinct whole-apk padding'})
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            self.assertEqual(report['libraries'][0]['classification'], 'identical_bytes')
            self.assertTrue(report['verdict']['all_compared_libraries_identical_bytes'])
            self.assertFalse(report['verdict']['exact_whole_apk_identity'])
            self.assertEqual(report['verdict']['application_equivalence'], 'not_evaluated_by_this_tool')

    def test_same_runtime_markers_different_application_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            write_apk(b, {'lib/arm64-v8a/libapp.so': elf(64, 183).replace(b'libc.so', b'libm.so')})
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            entry = report['libraries'][0]
            self.assertEqual(entry['classification'], 'runtime_marker_match_bytes_differ')
            self.assertIn('not evidence of application equivalence', entry['note'])
            self.assertTrue(report['verdict']['runtime_compatibility_clues_only'])
            self.assertFalse(report['verdict']['all_compared_libraries_identical_bytes'])
            self.assertEqual(report['verdict']['application_equivalence'], 'not_evaluated_by_this_tool')

    def test_different_isa_is_a_mismatch_not_a_clue(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            write_apk(b, {'lib/arm64-v8a/libapp.so': elf(64, 62)})
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            self.assertEqual(report['libraries'][0]['classification'], 'runtime_marker_mismatch')
            self.assertTrue(report['verdict']['mismatches_present'])

    def test_library_present_only_on_one_side_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': elf(64, 183), 'lib/arm64-v8a/libextra.so': elf(64, 183)})
            write_apk(b, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            classifications = {e['name']: e['classification'] for e in report['libraries']}
            self.assertEqual(classifications['libextra.so'], 'reference_only')
            self.assertTrue(report['verdict']['mismatches_present'])

    def test_exact_whole_apk_identity_requires_identical_input_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            b.write_bytes(a.read_bytes())
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            self.assertTrue(report['verdict']['exact_whole_apk_identity'])
            self.assertEqual(report['input_identity']['reference_sha256'], report['input_identity']['candidate_sha256'])

    def test_uninspected_libraries_are_reported_as_uncompared_not_matched(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.apk', Path(d) / 'b.apk'
            write_apk(a, {'lib/arm64-v8a/libapp.so': b'not an elf at all'})
            write_apk(b, {'lib/arm64-v8a/libapp.so': elf(64, 183)})
            report = compare_mod.compare(profile.profile(a), profile.profile(b))
            self.assertEqual(report['libraries'][0]['classification'], 'uncompared')
            self.assertFalse(report['verdict']['all_compared_libraries_identical_bytes'])


if __name__ == '__main__':
    unittest.main()
