"""Owned ELF fixtures: dependency evidence, not runtime compatibility claims."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import apk_native_profile as profile


def elf(bits=32, machine=40):
    wide = bits == 64
    data = bytearray(512)
    data[:16] = b'\x7fELF' + bytes([2 if wide else 1, 1, 1]) + bytes(9)
    header = 64 if wide else 52
    phsize = 56 if wide else 32
    dynamic, strings = (192, 320) if wide else (128, 256)
    tags = [(1, 1), (5, 0x1000 + strings), (10, 19), (14, 9), (0, 0)]
    dsize = len(tags) * (16 if wide else 8)
    struct.pack_into('<' + ('HHIQQQIHHHHHH' if wide else 'HHIIIIIHHHHHH'), data, 16,
                     3, machine, 1, 0, header, 0, 0, header, phsize, 2, 0, 0, 0)
    for index, (kind, offset, size) in enumerate([(1, 0, 512), (2, dynamic, dsize)]):
        if wide:
            values = (kind, 4, offset, 0x1000 + offset, 0, size, size, 8)
        else:
            values = (kind, offset, 0x1000 + offset, 0, size, size, 4, 4)
        struct.pack_into('<' + ('IIQQQQQQ' if wide else 'IIIIIIII'), data, header + index * phsize, *values)
    for index, tag in enumerate(tags):
        struct.pack_into('<' + ('qQ' if wide else 'iI'), data, dynamic + index * (16 if wide else 8), *tag)
    data[strings:strings + 19] = b'\0libc.so\0libapp.so\0'
    return bytes(data)


class NativeProfileTests(unittest.TestCase):
    def test_stripped_32_and_64_program_headers(self):
        for bits, machine in [(32, 40), (64, 183), (32, 3), (64, 62)]:
            with self.subTest(bits=bits, machine=machine):
                p = profile.elf_profile(elf(bits, machine))
                self.assertEqual(p['bits'], bits)
                self.assertEqual(p['needed'], ['libc.so'])
                self.assertEqual(p['sonames'], ['libapp.so'])

    def test_mixed_invalid_and_mislabelled_libraries_preserve_uncertainty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'mixed.apk'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('classes.dex', b'owned placeholder')
                z.writestr('lib/armeabi-v7a/libapp.so', elf())
                z.writestr('lib/arm64-v8a/libapp.so', elf(32))
                z.writestr('lib/arm64-v8a/libbad.so', b'broken')
            r = profile.profile(p)
            self.assertTrue(r['managed_dex_present'])
            records = {a['entry']: a for a in r['libraries']}
            self.assertFalse(records['lib/arm64-v8a/libapp.so']['abi_matches_payload'])
            self.assertEqual(records['lib/arm64-v8a/libbad.so']['status'], 'invalid-or-unsupported')
            self.assertEqual(r['graphs_by_declared_abi']['armeabi-v7a']['edges'][0]['packaged_candidates'], [])

    def test_budget_and_duplicate_paths_do_not_choose_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'budget.apk'
            with zipfile.ZipFile(p, 'w') as z, warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('lib/x86/libduplicate.so', elf(32, 3))
                z.writestr('lib/x86/libduplicate.so', elf(32, 3))
                z.writestr('lib/x86/libother.so', elf(32, 3))
            with patch.object(profile, 'MAX_TOTAL', 1):
                r = profile.profile(p)
            self.assertEqual(r['bounds']['decoded_bytes'], 0)
            self.assertTrue(all(a['status'] == 'uninspected' for a in r['libraries']))
            self.assertEqual(r['graphs_by_declared_abi'], {})

    def test_out_of_bounds_program_header_rejected(self):
        data = bytearray(elf())
        struct.pack_into('<I', data, 28, 500)
        with self.assertRaisesRegex(ValueError, 'header table'):
            profile.elf_profile(bytes(data))

    def test_different_abi_dependencies_are_not_merged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'different.apk'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('lib/armeabi-v7a/libapp.so', elf())
                z.writestr('lib/arm64-v8a/libapp.so', elf(64, 183).replace(b'libc.so', b'libm.so'))
            r = profile.profile(p)
            self.assertEqual(r['graphs_by_declared_abi']['armeabi-v7a']['edges'][0]['needed'], 'libc.so')
            self.assertEqual(r['graphs_by_declared_abi']['arm64-v8a']['edges'][0]['needed'], 'libm.so')

    def test_failed_crc_still_consumes_attempt_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'crc.apk'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('lib/x86/liba.so', elf(32, 3))
                z.writestr('lib/x86/libb.so', elf(32, 3))
            data = bytearray(p.read_bytes())
            data[30 + len('lib/x86/liba.so') + 10] ^= 1
            p.write_bytes(data)
            with patch.object(profile, 'MAX_TOTAL', 800):
                r = profile.profile(p)
            self.assertEqual([x['status'] for x in r['libraries']], ['invalid-or-unsupported', 'uninspected'])
            self.assertEqual(r['bounds']['charged_read_bytes'], 513)

    def test_empty_archive_does_not_claim_pure_java(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'empty.apk'
            with zipfile.ZipFile(p, 'w'):
                pass
            r = profile.profile(p)
            self.assertEqual(r['libraries'], [])
            self.assertIn('No native libraries found does not establish a pure Java app.', r['limits'][3])
