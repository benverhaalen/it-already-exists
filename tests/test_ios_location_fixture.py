import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "skills/reference-driven-development/scripts/ios_location_fixture.py"
SPEC = importlib.util.spec_from_file_location("ios_location_fixture", SOURCE)
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


class LocationFixtureTests(unittest.TestCase):
    def test_invalid_coordinates_and_exhausted_trajectory(self):
        for value in ("nan,0", "0,inf", "91,0", "0,-181", "0,0,0"):
            with self.assertRaises(argparse.ArgumentTypeError):
                fixture.coordinate(value)
        with self.assertRaises(ValueError):
            fixture.trajectory_speed((0, 0), (0, 0), 300)
        speed = fixture.trajectory_speed((0, 0), (0.001, 0), 300)
        self.assertGreater(speed, 0)
        self.assertAlmostEqual(111.1949266 / speed, 360, places=5)

    def run_case(self, command_result=0, state="Booted", start_error=False, cleanup_error=False, command_log="", required_text=()):
        calls = []
        executed = []

        def invoke(argv, **kwargs):
            calls.append(argv)
            if argv[2] == "list":
                data = {"devices": {"runtime": [{"udid": "owned-device", "state": state}]}}
                return subprocess.CompletedProcess(argv, 0, json.dumps(data), "")
            failed = (start_error and "start" in argv) or (cleanup_error and "clear" in argv)
            return subprocess.CompletedProcess(argv, int(failed), "", "")

        def execute(argv, timeout, log):
            executed.append(argv)
            log.write_text(command_log)
            if isinstance(command_result, Exception):
                raise command_result
            return command_result

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-evidence"
            result = fixture.run_fixture("owned-device", "test.bundle", (0, 0), (0.001, 0), 30,
                                         ["test-command"], output, invoke=invoke, execute=execute, required_text=required_text)
            self.assertEqual(json.loads((output / "receipt.json").read_text()), result)
        return result, calls, executed

    def test_failed_and_timed_out_tests_always_clear_fixture(self):
        for failure in (2, subprocess.TimeoutExpired(["secret-argument"], 30)):
            result, calls, executed = self.run_case(failure)
            self.assertFalse(result["fixture_command_passed"])
            self.assertTrue(result["cleanup_succeeded"])
            self.assertEqual(calls[-1][2:], ["location", "owned-device", "clear"])
            self.assertEqual(len(executed), 1)
            self.assertNotIn("secret-argument", json.dumps(result))
            self.assertFalse(any("privacy" in call for call in calls))

    def test_start_failure_is_not_retried_and_cleanup_failure_is_not_success(self):
        result, calls, executed = self.run_case(start_error=True)
        self.assertFalse(result["fixture_command_passed"])
        self.assertTrue(result["cleanup_succeeded"])
        self.assertFalse(executed)
        self.assertEqual(sum("start" in call for call in calls), 1)
        result, _, _ = self.run_case(cleanup_error=True)
        self.assertEqual(result["test_exit"], 0)
        self.assertFalse(result["fixture_command_passed"])

    def test_shutdown_device_does_not_mutate_permissions_or_location(self):
        result, calls, executed = self.run_case(state="Shutdown")
        self.assertFalse(result["fixture_command_passed"])
        self.assertEqual(len(calls), 1)
        self.assertFalse(executed)

    def test_actual_command_timeout_terminates_owned_process(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.TimeoutExpired):
                fixture.run_command([sys.executable, "-c", "import time; time.sleep(30)"],
                                    0.05, Path(directory) / "command.log")

    def test_zero_exit_without_selected_test_execution_witness_is_not_pass(self):
        result, _, _ = self.run_case(command_log="Executed 0 tests\nTEST SUCCEEDED", required_text=["selected_test passed"])
        self.assertEqual(result["test_exit"], 0)
        self.assertTrue(result["cleanup_succeeded"])
        self.assertFalse(result["fixture_command_passed"])
        result, _, _ = self.run_case(command_log="selected_test passed\nrequired_transition passed", required_text=["selected_test passed", "required_transition passed"])
        self.assertTrue(result["fixture_command_passed"])
        result, _, _ = self.run_case(command_log="selected_test passed", required_text=["selected_test passed", "required_transition passed"])
        self.assertFalse(result["fixture_command_passed"])


if __name__ == "__main__":
    unittest.main()
