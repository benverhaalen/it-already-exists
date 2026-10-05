import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/reference-driven-development/scripts/rdd.py"
SPEC = importlib.util.spec_from_file_location("rdd", SCRIPT)
rdd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rdd)


def record(identifier, kind, links=(), **extra):
    data = {field: f"explicit {field}" for field in rdd.REQUIRED[kind]}
    data.update(links=list(links))
    if kind == "evidence":
        data["basis"] = "observed"
    elif kind == "decision":
        data["status"] = "candidate"
    elif kind == "check":
        data["outcome"] = "not-run"
    data.update(extra)
    return {"id": identifier, "kind": kind, "data": data}


class ReferenceRecordsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "records.jsonl"

    def add(self, identifier, kind, links=(), **extra):
        return rdd.append(self.store, record(identifier, kind, links, **extra))

    def contribution(self):
        self.add("ref", "reference")
        self.add("evidence", "evidence", ["ref"])
        self.add("contribution", "contribution", ["evidence"], delta="fewer missed errors", property="Visible Validation")

    def assertRejectedUnchanged(self, item):
        before = self.store.read_bytes() if self.store.exists() else None
        with self.assertRaises(rdd.JournalError):
            rdd.append(self.store, item)
        after = self.store.read_bytes() if self.store.exists() else None
        self.assertEqual(before, after)

    def test_complete_chain_and_lexical_query(self):
        self.contribution()
        self.add("decision", "decision", ["contribution"], status="adopted")
        self.add("transfer", "transfer", ["contribution"])
        self.add("check", "check", ["transfer"], outcome="passed")
        self.add("lesson", "lesson", ["check"])
        records, _ = rdd.read_records(self.store)
        self.assertEqual(len(records), 7)
        self.assertEqual([r["id"] for r in rdd.query(records, term="visible VALIDATION", kind="contribution")], ["contribution"])
        self.assertEqual(list(rdd.query(records, neglected=True)), [])

    def test_delta_and_conditions_are_retained_per_contribution(self):
        self.contribution()
        self.add("alternative", "contribution", ["evidence"], delta={"before": 5, "after": 2}, conditions=["small screens"], test="count missed warnings")
        records, _ = rdd.read_records(self.store)
        self.assertEqual(records[2]["data"]["delta"], "fewer missed errors")
        self.assertEqual(records[3]["data"]["delta"], {"before": 5, "after": 2})
        self.assertEqual(records[3]["data"]["conditions"], ["small screens"])
        bad = record("missing-delta", "contribution", ["evidence"])
        del bad["data"]["delta"]
        self.assertRejectedUnchanged(bad)

    def test_latest_decision_controls_neglect_and_history_is_preserved(self):
        self.contribution()
        self.add("adopt", "decision", ["contribution"], status="adopted")
        records, _ = rdd.read_records(self.store)
        self.assertEqual(len(list(rdd.query(records, neglected=True))), 1)  # no transfer
        self.add("transfer", "transfer", ["contribution"])
        prior = self.store.read_bytes()
        self.add("reconsider", "decision", ["contribution"], status="contradicted", reason="failed in use")
        self.assertTrue(self.store.read_bytes().startswith(prior))
        records, _ = rdd.read_records(self.store)
        self.assertEqual([r["id"] for r in rdd.query(records, neglected=True)], ["contribution"])
        self.assertEqual([r["data"]["status"] for r in records if r["kind"] == "decision"], ["adopted", "contradicted"])
        self.add("readopt", "decision", ["contribution"], status="adopted")
        records, _ = rdd.read_records(self.store)
        self.assertEqual(list(rdd.query(records, neglected=True)), [])

    def test_typed_links_unique_ids_and_required_fields(self):
        self.contribution()
        for item in [
            record("ref", "reference"),
            record("bad", "evidence", ["missing"]),
            record("bad", "evidence", ["contribution"]),
            record("bad", "decision", ["ref"]),
            record("bad", "transfer", ["evidence"]),
            record("bad", "check", ["contribution"]),
            record("bad", "lesson", ["evidence"]),
            record("bad", "evidence", ["ref"], basis="certain"),
            record("bad", "decision", ["contribution"], status="approved"),
            record("bad", "check", ["ref"], outcome="success"),
            record("bad", "reference", inspection=" "),
        ]:
            with self.subTest(item=item):
                self.assertRejectedUnchanged(item)
        self.add("second", "contribution", ["evidence"])
        self.assertRejectedUnchanged(record("bad", "decision", ["contribution", "second"]))

    def test_local_hash_capture_and_drift_block_append(self):
        capture = self.store.parent / "capture.txt"
        capture.write_text("inspected content", encoding="utf-8")
        self.add("ref", "reference")
        item = record("evidence", "evidence", ["ref"], local_path="capture.txt")
        saved = rdd.append(self.store, item)
        self.assertEqual(saved["data"]["sha256"], rdd.digest(capture))
        self.assertNotIn("sha256", item["data"])
        rdd.read_records(self.store)
        capture.write_text("changed content", encoding="utf-8")
        with self.assertRaisesRegex(rdd.JournalError, "hash drift"):
            rdd.read_records(self.store)
        self.assertRejectedUnchanged(record("new", "reference"))

    def test_existing_corruption_blocks_append(self):
        self.add("ref", "reference")
        with self.store.open("ab") as stream:
            stream.write(b'{"truncated":')
        self.assertRejectedUnchanged(record("new", "reference"))

    def test_invalid_new_journal_does_not_create_file(self):
        self.assertRejectedUnchanged(record("bad", "evidence", ["missing"]))
        self.assertFalse(self.store.exists())

    def test_cli_append_check_query_and_failure(self):
        source = self.store.parent / "input.json"
        source.write_text(json.dumps(record("ref", "reference", job="Inspect interaction")), encoding="utf-8")
        def run(*args):
            return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(run("append", self.store, "--record", source).returncode, 0)
        checked = run("check", self.store)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("1 records", checked.stdout)
        found = run("query", self.store, "--term", "INTERACTION", "--kind", "reference")
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout)["id"], "ref")
        before = self.store.read_bytes()
        self.assertEqual(run("append", self.store, "--record", source).returncode, 1)
        self.assertEqual(before, self.store.read_bytes())


if __name__ == "__main__":
    unittest.main()
