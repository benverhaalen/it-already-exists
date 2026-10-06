import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/reference-driven-development/scripts'))
import flutter_wire_inspect as wire


class WireTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads((ROOT / 'tests/fixtures/flutter-wire/vectors.json').read_text())

    def decode(self, data, **kwargs):
        return wire.inspect_message(data, byte_order='little', **kwargs)['root']

    def test_upstream_java_primitives_preserve_wire_identity(self):
        raw = bytes.fromhex(self.golden['vectors']['primitives']['hex'])
        items = self.decode(raw)['items']
        self.assertEqual([x['type'] for x in items],
                         ['true', 'false', 'int32', 'float64', 'int64', 'null', 'string'])
        self.assertEqual([x['value'] for x in items], [True, False, 1, 1.0, 9007199254740993, None, 'é'])
        self.assertEqual(items[3]['offset'], 9)
        self.assertEqual(items[3]['padding_hex'], '000000000000')

    def test_upstream_nested_custom_and_typed_array_alignment(self):
        raw = bytes.fromhex(self.golden['vectors']['nested-alignment']['hex'])
        root = self.decode(raw, custom_tags=(200, 201))
        items = root['items']
        nested = items[0]['wrapped']['items'][0]['wrapped']
        self.assertEqual(nested['type'], 'float64')
        self.assertEqual(nested['value'], 0.5)
        self.assertEqual(nested['end'], 16)
        self.assertEqual(items[1]['values'], [-1, 2147483647])
        self.assertEqual(items[2]['values'], [-(1 << 63), (1 << 63) - 1])
        self.assertEqual(items[3]['values'], [1.5, -2.5])
        self.assertEqual(items[4]['values'], [-0.0, '+inf'])
        self.assertEqual(items[5]['bits_hex'], '0001ff')
        self.assertEqual(root['end'], len(raw))
        with self.assertRaisesRegex(ValueError, 'Unknown tag'):
            self.decode(raw)

    def test_upstream_sizes_and_big_integer_text(self):
        for name, data in [('size254', bytes.fromhex('07fefe00') + b'x' * 254),
                           ('size65536', bytes.fromhex('07ff00000100') + b'y' * 65536)]:
            self.assertEqual(hashlib.sha256(data).hexdigest(), self.golden['vectors'][name]['sha256'])
            self.assertEqual(len(data), self.golden['vectors'][name]['bytes'])
            self.assertEqual(len(self.decode(data)['value']), int(name[4:]))
        node = self.decode(bytes.fromhex(self.golden['vectors']['bigint']['hex']))
        self.assertEqual(node['type'], 'large-int-text')
        self.assertEqual(node['value'], '-123456789abcdef')

    def test_map_keys_duplicate_keys_and_endianness(self):
        pairs = self.decode(bytes.fromhex(self.golden['vectors']['map']['hex']))['pairs']
        self.assertEqual([pair[0]['type'] for pair in pairs], ['int32', 'true'])
        duplicate = self.decode(bytes.fromhex('0d02030100000000030100000001'))['pairs']
        self.assertEqual(len(duplicate), 2)
        node = wire.inspect_message(b'\x03' + struct.pack('>i', -123), byte_order='big')['root']
        self.assertEqual(node['value'], -123)

    def test_malformed_messages_limits_and_separately_encoded_double(self):
        # A standalone scalar double carries seven padding bytes; inserting it
        # behind this list header leaves two trailing bytes. Re-align the payload
        # at the complete-message offset instead of copying its standalone pad.
        standalone = b'\x06' + b'\0' * 7 + struct.pack('<d', 0.5)
        self.assertEqual(self.decode(standalone)['value'], 0.5)
        with self.assertRaisesRegex(ValueError, 'Trailing bytes'):
            self.decode(b'\x0c\x01' + standalone)
        for data in [b'', b'\x03', b'\x07\xff\xff\xff\xff\xff', b'\x07\x01\xff',
                     b'\x0f', b'\x00\x00', b'\x0c\xff\xff\xff\xff\xff']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.decode(data)
        with self.assertRaisesRegex(ValueError, 'Depth'):
            self.decode(b'\x0c\x01' * 65 + b'\x00')
        with self.assertRaisesRegex(ValueError, 'Node budget'):
            self.decode(b'\x08\x03abc', max_nodes=3)
        for kwargs in [{'custom_tags': [1]}, {'max_nodes': True}, {'max_depth': 65}]:
            with self.assertRaises(ValueError):
                self.decode(b'\x00', **kwargs)

    def test_cli_private_output_no_overwrite_or_capture_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'capture.bin', Path(directory) / 'trace.json'
            source.write_bytes(bytes.fromhex(self.golden['vectors']['primitives']['hex']))
            command = [sys.executable, wire.__file__, str(source), '--byte-order', 'little',
                       '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            before = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), before)
            output.unlink()
            source.write_bytes(b'\x07\x06secret\x00')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('secret', result.stderr + result.stdout)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
