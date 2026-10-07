import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/reference-driven-development/scripts/json_state_delta.py"
spec = importlib.util.spec_from_file_location("json_state_delta", SCRIPT)
delta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)


class StateDeltaTests(unittest.TestCase):
    def test_types_precision_and_signed_zero_are_not_silently_equal(self):
        for old, new in [(True, 1), (1, 1.0), (2**53, 2**53 + 1), (0.0, -0.0)]:
            with self.subTest(old=old, new=new):
                self.assertFalse(delta.compare_states(old, new)["equal"])
        self.assertTrue(delta.compare_states({"a": 1, "b": 2}, {"b": 2, "a": 1})["equal"])

    def test_missing_null_escaped_keys_and_array_identity(self):
        result = delta.compare_states({"a/b~": None, "items": [1, 2]}, {"items": [2]})
        self.assertEqual([(x["pointer"], x["kind"]) for x in result["changes"]],
                         [("/a~1b~0", "removed"), ("/items", "array_length_changed")])
        self.assertEqual(delta.compare_states([1, 2], [1, 3])["changes"][0]["pointer"], "/1")

    def test_rejects_ambiguous_or_unbounded_inputs(self):
        for value in [float("nan"), float("inf"), {1: "x"}]:
            with self.assertRaises(ValueError):
                delta.compare_states(value, value)
        value = None
        for _ in range(delta.MAX_DEPTH + 1):
            value = [value]
        with self.assertRaises(ValueError):
            delta.compare_states(value, value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"same": 1, "same": 2}')
            with self.assertRaises(ValueError):
                delta.read_state(path)

    def test_cli_retains_sources_and_does_not_emit_changed_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after, output = [root / name for name in ("before.json", "after.json", "delta.json")]
            before.write_text(json.dumps({"token": "private-before-value"}))
            after.write_text(json.dumps({"token": "private-after-value"}))
            original = before.read_bytes(), after.read_bytes()
            command = [sys.executable, str(SCRIPT), "--before", str(before), "--after", str(after), "--output", str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            for secret in ("private-before-value", "private-after-value"):
                self.assertNotIn(secret, run.stdout + run.stderr + output.read_text())
            saved = output.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual((before.read_bytes(), after.read_bytes()), original)


if __name__ == "__main__":
    unittest.main()
