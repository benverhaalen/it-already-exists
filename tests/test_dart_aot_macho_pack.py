"""Owned layout fixtures; no third-party executable bytes or fidelity claims."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'))
import dart_aot_macho_pack as packer


def fixture():
    data = bytearray(32784)
    data[:16] = b'\x7fELF\x02\x01\x01' + bytes(9)
    struct.pack_into('<HHIQQQIHHHHHH', data, 16,
                     3, 183, 1, 0, 64, 1024, 0, 64, 56, 3, 64, 4, 1)
    for i, (flags, offset, size, memory) in enumerate(
            [(4, 0, 4096, 4096), (5, 16384, 4096, 4096), (6, 32768, 16, 32)]):
        struct.pack_into('<IIQQQQQQ', data, 64+i*56,
                         1, flags, offset, offset, 0, size, memory, 16384)
    names = b'\0.shstrtab\0.dynstr\0.dynsym\0'
    data[512:512+len(names)] = names
    strings = b'\0'
    indices = []
    for name in packer.SYMBOLS:
        indices.append(len(strings))
        strings += name.encode() + b'\0'
    data[600:600+len(strings)] = strings
    sections = [(1, 3, 512, len(names), 0, 0),
                (11, 3, 600, len(strings), 0, 0),
                (19, 11, 800, 120, 2, 24)]
    for i, (name, kind, offset, size, link, entry) in enumerate(sections, 1):
        struct.pack_into('<IIQQQQIIQQ', data, 1024+i*64,
                         name, kind, 0, 0, offset, size, link, 0, 8, entry)
    for i, (name, address) in enumerate(zip(indices, [2048, 16384, 2056, 16392]), 1):
        struct.pack_into('<IBBHQQ', data, 800+i*24, name, 0x11, 0, 1, address, 8)
    return data


class PackTests(unittest.TestCase):
    def test_exact_bytes_and_zero_fill_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.so'
            source.write_bytes(fixture())
            output = Path(directory) / 'output'
            receipt = packer.pack(source, output)
            self.assertEqual((output / 'snapshot.bin').read_bytes(), source.read_bytes())
            self.assertEqual(receipt['writable_offset'], 32768)
            assembly = (output / 'snapshot.S').read_text()
            self.assertIn(',32768,16', assembly)
            self.assertIn('.space 16', assembly)
            self.assertIn('application equivalence', receipt['not_verified'])
            with self.assertRaises(FileExistsError):
                packer.pack(source, output)

    def test_bad_geometry_refused_before_output(self):
        mutations = [
            (64+56+8, '<Q', 16000, 'Non-identity'),
            (64+112+16, '<Q', 32000, 'Non-identity'),
            (64+112+4, '<I', 7, 'permissions'),
            (64+40, '<Q', 4097, 'Non-final zero-fill'),
            (40, '<Q', 32780, 'Header table'),
            (62, '<H', 4, 'section-name'),
            (800+24+8, '<Q', 16384, 'permissions'),
            (800+48, '<I', 1, 'Ambiguous'),
            (800+24+8, '<Q', 4095, 'file-backed'),
        ]
        for offset, format_, value, reason in mutations:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                data = fixture()
                struct.pack_into(format_, data, offset, value)
                source = Path(directory) / 'bad.so'
                source.write_bytes(data)
                output = Path(directory) / 'output'
                with self.assertRaisesRegex(ValueError, reason):
                    packer.pack(source, output)
                self.assertFalse(output.exists())

    def test_assembly_path_quoting_and_control_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.so'
            source.write_bytes(fixture())
            output = Path(directory) / 'a"b'
            packer.pack(source, output)
            self.assertIn('a\\"b', (output / 'snapshot.S').read_text())
            invalid = Path(directory) / 'line\nbreak'
            with self.assertRaisesRegex(ValueError, 'Control characters'):
                packer.pack(source, invalid)
            self.assertFalse(invalid.exists())


if __name__ == '__main__':
    unittest.main()
