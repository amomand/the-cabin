from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_ios_lane.py"
SPEC = importlib.util.spec_from_file_location("cabin_run_ios_lane", SCRIPT)
assert SPEC and SPEC.loader
lane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lane)


class IOSLaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.cache = Path(self.tempdir.name) / "cache"
        self.output = Path(self.tempdir.name) / "evidence"
        self.root.mkdir()
        self.cache.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_passed_lane_retains_hashed_xcode_log(self) -> None:
        devices = json.dumps(
            {
                "devices": {
                    "runtime": [
                        {
                            "name": "iPhone Air",
                            "udid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                            "isAvailable": True,
                        }
                    ]
                }
            }
        )

        def fake_run(command, cwd, *, env=None):
            if command[:4] == ["xcrun", "simctl", "list", "devices"]:
                return subprocess.CompletedProcess(command, 0, devices, "")
            if command[0] == "xcodebuild":
                self.assertNotIn("OPENAI_API_KEY", env)
                self.assertNotIn("CABIN_LOCAL_OPENAI_API_KEY", env)
                return subprocess.CompletedProcess(command, 0, "** TEST SUCCEEDED **\n", "")
            raise AssertionError(command)

        with mock.patch.object(lane, "prepare_runtime", return_value="compatible-cache"):
            with mock.patch.object(lane, "run", side_effect=fake_run):
                with mock.patch.dict(
                    lane.os.environ,
                    {"OPENAI_API_KEY": "secret", "CABIN_LOCAL_OPENAI_API_KEY": "secret"},
                ):
                    value = lane.execute(self.root, self.cache, self.output, "iPhone Air")

        self.assertEqual(value["status"], "passed")
        log = Path(value["log_path"])
        self.assertEqual(log.read_text(encoding="utf-8"), "** TEST SUCCEEDED **\n")
        self.assertEqual(value, json.loads((self.output / "ios-evidence.json").read_text()))

    def test_missing_simulator_is_a_retained_coverage_gap(self) -> None:
        completed = subprocess.CompletedProcess(
            ["xcrun"],
            0,
            json.dumps({"devices": {"runtime": []}}),
            "",
        )
        with mock.patch.object(lane, "prepare_runtime", return_value="compatible-cache"):
            with mock.patch.object(lane, "run", return_value=completed):
                value = lane.execute(self.root, self.cache, self.output, "iPhone Air")

        self.assertEqual(value["status"], "unavailable")
        self.assertIn("no available iOS Simulator", value["detail"])
        self.assertTrue(Path(value["log_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
