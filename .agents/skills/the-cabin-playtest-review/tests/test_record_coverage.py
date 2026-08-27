from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "record_coverage.py"
SPEC = importlib.util.spec_from_file_location("cabin_record_coverage", SCRIPT)
assert SPEC and SPEC.loader
history_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(history_module)


class CoverageHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest = self.root / "run" / "evidence-manifest.json"
        self.result = self.root / "run" / "result.json"
        self.probe_manifest = self.root / "run" / "probe-manifest.json"
        self.history = self.root / "coverage-history.json"
        self.manifest.parent.mkdir()
        source_sha = "a" * 40
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "source_sha": source_sha,
                    "previous_source_sha": source_sha,
                    "review_kind": "experiential",
                }
            ),
            encoding="utf-8",
        )
        self.result.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "source_sha": source_sha,
                    "previous_source_sha": source_sha,
                    "review_kind": "experiential",
                    "outcome": "noop",
                    "probed_routes": ["reports/probes/a.txt", "reports/probes/b.txt"],
                    "probe_families": ["guidance", "save-load"],
                    "terminal_web_status": "passed",
                    "ios_evidence": {"status": "passed"},
                }
            ),
            encoding="utf-8",
        )
        self.probe_manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_sha": source_sha,
                    "probes": [],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def append(self, run_id: str = "run-a", issue_urls: list[str] | None = None):
        return history_module.append_history(
            self.history,
            run_id,
            "2026-08-27T15:30:00+03:00",
            self.manifest,
            self.probe_manifest,
            self.result,
            issue_urls or [],
        )

    def test_appends_an_atomic_rotation_record(self) -> None:
        record = self.append()
        stored = json.loads(self.history.read_text(encoding="utf-8"))
        self.assertEqual(stored["runs"], [record])
        self.assertEqual(record["probe_families"], ["guidance", "save-load"])
        self.assertEqual(
            record["manifest_sha256"],
            hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
        )

    def test_rejects_duplicate_run_id(self) -> None:
        self.append()
        with self.assertRaisesRegex(history_module.HistoryError, "already contains"):
            self.append()

    def test_requires_issue_urls_exactly_for_issue_outcome(self) -> None:
        result = json.loads(self.result.read_text(encoding="utf-8"))
        result["outcome"] = "issues"
        self.result.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(history_module.HistoryError, "issue URLs"):
            self.append()
        record = self.append(
            issue_urls=["https://github.com/amomand/the-cabin/issues/246"]
        )
        self.assertEqual(record["issue_urls"], ["https://github.com/amomand/the-cabin/issues/246"])

    def test_concurrent_writers_retain_every_distinct_run(self) -> None:
        processes = []
        for index in range(16):
            command = [
                sys.executable,
                str(SCRIPT),
                "--history",
                str(self.history),
                "--run-id",
                f"run-{index}",
                "--recorded-at",
                "2026-08-27T15:30:00+03:00",
                "--manifest",
                str(self.manifest),
                "--result",
                str(self.result),
                "--probe-manifest",
                str(self.probe_manifest),
            ]
            processes.append(
                subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        completed = [process.communicate(timeout=20) for process in processes]
        self.assertTrue(
            all(process.returncode == 0 for process in processes),
            completed,
        )
        history = json.loads(self.history.read_text(encoding="utf-8"))
        self.assertEqual(len(history["runs"]), 16)
        self.assertEqual(
            {run["run_id"] for run in history["runs"]},
            {f"run-{index}" for index in range(16)},
        )


if __name__ == "__main__":
    unittest.main()
