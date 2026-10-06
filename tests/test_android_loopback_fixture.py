import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/reference-driven-development/scripts"
sys.path.insert(0, str(SCRIPTS))
import android_loopback_fixture as fixture
sys.path.pop(0)


class LoopbackFixtureTests(unittest.TestCase):
    def run_case(self, initial=None, failure=None, cleanup_failure=False, changed=False, create_failure=False, required_text=(), log_text=""):
        mapping = dict(initial or {})
        calls, executed = [], []

        def invoke(argv, **kwargs):
            self.assertEqual(argv[1:3], ["-s", "emulator-5560"])
            calls.append(argv[3:])
            args = argv[3:]
            if args == ["get-state"]:
                return subprocess.CompletedProcess(argv, 0, "device\n", "")
            if args == ["reverse", "--list"]:
                text = "".join(f"transport {a} {b}\n" for a, b in mapping.items())
                return subprocess.CompletedProcess(argv, 0, text, "")
            if args[1] == "--no-rebind":
                if create_failure:
                    return subprocess.CompletedProcess(argv, 1, "", "")
                self.assertNotIn(args[2], mapping)
                mapping[args[2]] = args[3]
            elif args[1] == "--remove":
                if cleanup_failure:
                    return subprocess.CompletedProcess(argv, 1, "", "")
                mapping.pop(args[2])
            else:
                self.fail("Unexpected mutation")
            return subprocess.CompletedProcess(argv, 0, "", "")

        def execute(argv, timeout, log):
            executed.append(argv)
            log.write_text(log_text)
            if changed:
                mapping["tcp:8849"] = "tcp:9999"
            if isinstance(failure, Exception):
                raise failure
            return failure or 0

        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "private"
            result = fixture.run_fixture("adb", "emulator-5560", 8849, 8089,
                                         ["test"], 30, output, invoke, execute, required_text)
            self.assertEqual(result, json.loads((output / "receipt.json").read_text()))
        return result, calls, mapping, executed

    def test_conflict_refused_and_matching_route_borrowed_without_removal(self):
        r, calls, mapping, executed = self.run_case({"tcp:8849": "tcp:9999"})
        self.assertFalse(r["fixture_command_passed"])
        self.assertFalse(executed)
        self.assertFalse(any("--remove" in c or "--no-rebind" in c for c in calls))
        self.assertEqual(mapping["tcp:8849"], "tcp:9999")
        r, calls, _, _ = self.run_case({"tcp:8849": "tcp:8089"}, failure=2)
        self.assertTrue(r["borrowed"])
        self.assertFalse(r["fixture_command_passed"])
        self.assertFalse(any("--remove" in c for c in calls))

    def test_failed_and_timed_out_commands_cleanup_only_created_route(self):
        for failure in (2, subprocess.TimeoutExpired(["secret"], 30), None):
            r, _, mapping, executed = self.run_case({"tcp:5000": "tcp:5001"}, failure)
            self.assertTrue(r["cleanup_succeeded"])
            self.assertEqual(mapping, {"tcp:5000": "tcp:5001"})
            self.assertEqual(len(executed), 1)
            self.assertEqual(r["fixture_command_passed"], failure is None)
            self.assertNotIn("secret", json.dumps(r))

    def test_cleanup_error_or_replaced_route_cannot_pass(self):
        r, _, _, _ = self.run_case(cleanup_failure=True)
        self.assertFalse(r["fixture_command_passed"])
        r, calls, mapping, _ = self.run_case(changed=True)
        self.assertFalse(r["fixture_command_passed"])
        self.assertEqual(mapping["tcp:8849"], "tcp:9999")
        self.assertFalse(any("--remove" in c for c in calls))

    def test_creation_failure_never_runs_command_or_removes_unknown_route(self):
        r, calls, _, executed = self.run_case(create_failure=True)
        self.assertFalse(r["fixture_command_passed"])
        self.assertFalse(executed)
        self.assertFalse(any("--remove" in c for c in calls))

    def test_zero_exit_without_completion_witness_cannot_pass(self):
        r, _, _, _ = self.run_case(required_text=("FLOW_COMPLETED",), log_text="0 tests")
        self.assertFalse(r["fixture_command_passed"])
        self.assertTrue(r["cleanup_succeeded"])
        r, _, _, _ = self.run_case(required_text=("FLOW_COMPLETED",), log_text="FLOW_COMPLETED")
        self.assertTrue(r["fixture_command_passed"])

    def test_ambiguous_listing_and_implicit_device_are_rejected(self):
        self.assertEqual(fixture.routes("transport tcp:1 tcp:2\n\n"), {"tcp:1": "tcp:2"})
        for text in ("missing fields", "t tcp:1 tcp:2\nt tcp:1 tcp:3"):
            with self.assertRaises(ValueError):
                fixture.routes(text)
        with self.assertRaises(ValueError):
            fixture.run_fixture("adb", "", 1, 2, ["test"], 30, Path("unused"))


if __name__ == "__main__":
    unittest.main()
