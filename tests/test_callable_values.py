import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'))
import callable_values as codec


def wrapped(value, unsigned=False):
    return {'@type': 'type.googleapis.com/google.protobuf.' + ('UInt64Value' if unsigned else 'Int64Value'),
            'value': str(value)}


class CallableValuesTest(unittest.TestCase):
    def test_cli_private_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            target = Path(directory) / 'decoded.json'
            source.write_text(json.dumps({'quantity': wrapped(1)}))
            command = [sys.executable, codec.__file__, str(source), '--output', str(target)]
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(json.loads(target.read_text()), {'quantity': 1})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            second = subprocess.run(command, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(json.loads(target.read_text()), {'quantity': 1})

    def test_documented_wire_values_and_nested_original_types(self):
        # The long values are the official protocol examples, not local encoders.
        payload = {'signed': wrapped('-123456789123456'), 'unsigned': wrapped('123456789123456', True),
                   'nested': [wrapped(1), wrapped(40), True, None, 1.5, '1']}
        before = copy.deepcopy(payload)
        self.assertEqual(codec.decode(payload), {'signed': -123456789123456, 'unsigned': 123456789123456,
                                                'nested': [1, 40, True, None, 1.5, '1']})
        self.assertEqual(payload, before)
        self.assertIs(type(codec.decode(payload)['nested'][2]), bool)

    def test_boundaries_and_malformed_typed_integers(self):
        for number, unsigned in [(-(1 << 63), False), ((1 << 63) - 1, False), ((1 << 64) - 1, True)]:
            self.assertEqual(codec.decode(wrapped(number, unsigned)), number)
        bad = [wrapped(-(1 << 63) - 1), wrapped(1 << 63), wrapped(-1, True), wrapped(1 << 64, True),
               wrapped('1.0'), wrapped('01'), wrapped('-0'), wrapped('1\n'), wrapped('9' * 1000),
               dict(wrapped(1), value=True), dict(wrapped(1), extra='unsupported')]
        for value in bad:
            with self.subTest(value=str(value)[:100]), self.assertRaises(ValueError):
                codec.decode(value)

    def test_unknown_types_retained_and_traversal_bounds(self):
        value = {'@type': 'future.example/type', 'value': {'nested': wrapped(4)}}
        self.assertEqual(codec.decode(value), {'@type': 'future.example/type', 'value': {'nested': 4}})
        for value, options in [([1, 2], {'max_nodes': 2}), ([[1]], {'max_depth': 1}),
                               (float('nan'), {}), ({1: 'invalid key'}, {}), ((1, 2), {})]:
            with self.assertRaises(ValueError):
                codec.decode(value, **options)


if __name__ == '__main__':
    unittest.main()
