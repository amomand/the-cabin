from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_result.py"
SPEC = importlib.util.spec_from_file_location("cabin_validate_result", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

PREPARE_SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_evidence.py"
PREPARE_SPEC = importlib.util.spec_from_file_location("cabin_prepare_evidence", PREPARE_SCRIPT)
assert PREPARE_SPEC and PREPARE_SPEC.loader
preparer = importlib.util.module_from_spec(PREPARE_SPEC)
PREPARE_SPEC.loader.exec_module(preparer)


class ValidateResultTests(unittest.TestCase):
    source_sha = "a" * 40

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        report = self.root / "reports/playtests/golden.txt"
        report.parent.mkdir(parents=True)
        report.write_text("report\n", encoding="utf-8")
        for relative in validator.EXPECTED_CONTEXT:
            context = self.root / relative
            context.parent.mkdir(parents=True, exist_ok=True)
            context.write_text("context\n", encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.result = self.root / "result.json"
        self.findings = self.root / "findings.json"
        self.ios_log = self.root / "ios-test.log"
        self.ios_log.write_text("** TEST SUCCEEDED **\n", encoding="utf-8")
        self.ios_evidence_file = self.root / "ios-evidence.json"
        (self.root / "DerivedData").mkdir()
        (self.root / "TheCabinTests.xcresult").mkdir()
        self.probe_paths = [
            "reports/probes/guidance.txt",
            "reports/probes/save-load.txt",
        ]
        for path in self.probe_paths:
            probe = self.root / path
            probe.parent.mkdir(parents=True, exist_ok=True)
            probe.write_text(
                f"# Playtest Report: {probe.stem}\n\nSurface: both\nResult: PASS\n",
                encoding="utf-8",
            )
        self.probe_manifest = self.root / "probe-manifest.json"
        self.probe_scenarios = []
        probe_records = []
        for index, (family, report_path) in enumerate(
            zip(("guidance", "save-load"), self.probe_paths, strict=True)
        ):
            scenario = self.root / f"probe-{index}.yaml"
            scenario.write_text(
                f"name: probe-{index}\nsurface: both\ncommands:\n  - look\noffline_ai: true\n",
                encoding="utf-8",
            )
            self.probe_scenarios.append(scenario)
            report = self.root / report_path
            probe_records.append(
                {
                    "family": family,
                    "scenario_name": f"probe-{index}",
                    "scenario_path": str(scenario),
                    "scenario_sha256": hashlib.sha256(scenario.read_bytes()).hexdigest(),
                    "scenario_content": scenario.read_text(encoding="utf-8"),
                    "runner_returncode": 0,
                    "report_path": report_path,
                    "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                    "report_content": report.read_text(encoding="utf-8"),
                }
            )
        self.write_json(
            self.probe_manifest,
            {
                "schema_version": 1,
                "workflow": "cabin-playtest-review",
                "source_sha": self.source_sha,
                "probes": probe_records,
            },
        )
        initial_ios_evidence = {
            "schema_version": 1,
            "status": "passed",
            "command": [
                "xcodebuild",
                "test",
                "-project",
                "ios/TheCabin.xcodeproj",
                "-scheme",
                "TheCabin",
                "-destination",
                "id=AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                "-derivedDataPath",
                str(self.root / "DerivedData"),
                "-resultBundlePath",
                str(self.root / "TheCabinTests.xcresult"),
            ],
            "destination": "iPhone Air",
            "detail": "The iOS lane completed.",
            "runtime_source": "compatible-cache",
            "log_path": str(self.ios_log),
            "log_sha256": hashlib.sha256(self.ios_log.read_bytes()).hexdigest(),
        }
        self.write_json(self.ios_evidence_file, initial_ios_evidence)
        self.write_json(
            self.manifest,
            {
                "schema_version": 2,
                "workflow": "cabin-playtest-review",
                "source_sha": self.source_sha,
                "previous_source_sha": None,
                "review_kind": "regression",
                "changed_paths": [],
                "change_areas": {area: 0 for area in validator.CHANGE_AREAS},
                "runner_returncode": 0,
                "reports": ["reports/playtests/golden.txt"],
                "report_sha256": {
                    "reports/playtests/golden.txt": hashlib.sha256(b"report\n").hexdigest(),
                },
                "report_contents": {"reports/playtests/golden.txt": "report\n"},
                "context": list(validator.EXPECTED_CONTEXT),
                "context_sha256": {
                    path: hashlib.sha256(b"context\n").hexdigest()
                    for path in validator.EXPECTED_CONTEXT
                },
                "ios_evidence": initial_ios_evidence,
            },
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def write_result(self, outcome: str, *, ios_status: str = "passed") -> None:
        command = (
            [
                "xcodebuild",
                "test",
                "-project",
                "ios/TheCabin.xcodeproj",
                "-scheme",
                "TheCabin",
                "-destination",
                "id=AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                "-derivedDataPath",
                str(self.root / "DerivedData"),
                "-resultBundlePath",
                str(self.root / "TheCabinTests.xcresult"),
            ]
            if ios_status != "unavailable"
            else []
        )
        uncovered = ["ios-device", "live-model"]
        if ios_status != "passed":
            uncovered.append("ios-simulator")
        ios_evidence = {
            "schema_version": 1,
            "status": ios_status,
            "command": command,
            "destination": "iPhone Air",
            "detail": "The iOS lane completed.",
            "runtime_source": "compatible-cache" if ios_status != "unavailable" else None,
            "log_path": str(self.ios_log),
            "log_sha256": hashlib.sha256(self.ios_log.read_bytes()).hexdigest(),
        }
        self.write_json(self.ios_evidence_file, ios_evidence)
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["ios_evidence"] = ios_evidence
        self.write_json(self.manifest, manifest)
        self.write_json(
            self.result,
            {
                "schema_version": 2,
                "workflow": "cabin-playtest-review",
                "mode": "active",
                "review_kind": "regression",
                "outcome": outcome,
                "source_sha": self.source_sha,
                "previous_source_sha": None,
                "reviewed_reports": ["reports/playtests/golden.txt"],
                "probed_routes": self.probe_paths,
                "probe_evidence": [
                    {
                        "path": path,
                        "sha256": hashlib.sha256(
                            (self.root / path).read_bytes()
                        ).hexdigest(),
                        "content": (self.root / path).read_text(encoding="utf-8"),
                    }
                    for path in self.probe_paths
                ],
                "probe_families": ["guidance", "save-load"],
                "terminal_web_status": "passed",
                "ios_evidence": ios_evidence,
                "live_model_status": "not-run",
                "uncovered_areas": sorted(uncovered),
                "summary": "Reviewed the deterministic pack.",
            },
        )

    def finding(self) -> dict[str, str]:
        evidence = "The golden path reports fear: 0 after the voicemail."
        reproduction = "Run playtests/scenarios/act1_to_act5_golden_path.yaml."
        return {
            "title": "The voicemail leaves fear untouched",
            "body": (
                "## What's wrong\n\nThe voicemail lands without consequence.\n\n"
                f"## Evidence\n\n{evidence}\n\n"
                "## Why it matters\n\nThe state contradicts the scene.\n\n"
                f"## Reproduction\n\n{reproduction}"
            ),
            "severity": "continuity",
            "evidence": evidence,
            "reproduction": reproduction,
        }

    def validate(self):
        def fake_git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "HEAD"):
                return self.source_sha
            if args[0] in {"status", "cat-file"}:
                return ""
            if args[0] in {"hash-object", "rev-parse"}:
                return "context-blob"
            raise AssertionError(f"unexpected git call: {args}")

        with mock.patch.object(validator, "git", side_effect=fake_git):
            return validator.validate(
                self.root,
                "active",
                self.source_sha,
                self.manifest,
                self.probe_manifest,
                self.result,
                self.findings,
            )

    def test_accepts_bounded_issue_result(self) -> None:
        self.write_result("issues")
        self.write_json(self.findings, [self.finding()])
        value = self.validate()
        self.assertEqual(value["findings"], 1)

    def test_accepts_noop_with_empty_findings(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        value = self.validate()
        self.assertEqual(value["outcome"], "noop")
        self.assertEqual(value["ios_status"], "passed")

    def test_accepts_coverage_gap_when_ios_lane_is_unavailable(self) -> None:
        self.write_result("coverage-gap", ios_status="unavailable")
        self.write_json(self.findings, [])
        value = self.validate()
        self.assertEqual(value["outcome"], "coverage-gap")

    def test_rejects_noop_when_ios_lane_is_unavailable(self) -> None:
        self.write_result("noop", ios_status="unavailable")
        self.write_json(self.findings, [])
        with self.assertRaisesRegex(validator.ValidationError, "noop requires clean"):
            self.validate()

    def test_rejects_coverage_gap_when_all_automated_lanes_pass(self) -> None:
        self.write_result("coverage-gap")
        self.write_json(self.findings, [])
        with self.assertRaisesRegex(validator.ValidationError, "incomplete evidence lane"):
            self.validate()

    def test_rejects_more_than_three_findings(self) -> None:
        self.write_result("issues")
        self.write_json(self.findings, [self.finding()] * 4)
        with self.assertRaisesRegex(validator.ValidationError, "at most three"):
            self.validate()

    def test_rejects_publisher_prefix_in_payload(self) -> None:
        self.write_result("issues")
        finding = self.finding()
        finding["title"] = "[playtest] Duplicate prefix"
        self.write_json(self.findings, [finding])
        with self.assertRaisesRegex(validator.ValidationError, "publisher prefix"):
            self.validate()

    def test_rejects_evidence_missing_from_body(self) -> None:
        self.write_result("issues")
        finding = self.finding()
        finding["evidence"] = "A different line."
        self.write_json(self.findings, [finding])
        with self.assertRaisesRegex(validator.ValidationError, "evidence must appear"):
            self.validate()

    def test_rejects_incomplete_context_pack(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["context"] = manifest["context"][:1]
        self.write_json(self.manifest, manifest)
        with self.assertRaisesRegex(validator.ValidationError, "exact context pack"):
            self.validate()

    def test_rejects_report_content_changed_after_preparation(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        report = self.root / "reports/playtests/golden.txt"
        report.write_text("report\nUNTRUSTED REPORT TAMPER PROBE\n", encoding="utf-8")
        with self.assertRaisesRegex(validator.ValidationError, "differs from the evidence manifest"):
            self.validate()

    def test_rejects_retained_report_content_that_differs(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["report_contents"]["reports/playtests/golden.txt"] = "different\n"
        self.write_json(self.manifest, manifest)
        with self.assertRaisesRegex(validator.ValidationError, "retained report content"):
            self.validate()

    def test_rejects_retained_probe_content_that_differs(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        result = json.loads(self.result.read_text(encoding="utf-8"))
        result["probe_evidence"][0]["content"] = "different\n"
        self.write_json(self.result, result)
        with self.assertRaisesRegex(validator.ValidationError, "retained probe content"):
            self.validate()

    def test_rejects_ios_log_that_differs_from_its_hash(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        self.ios_log.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(validator.ValidationError, "ios_evidence log differs"):
            self.validate()

    def test_rejects_ios_pass_from_an_unrelated_command_or_destination(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        result = json.loads(self.result.read_text(encoding="utf-8"))
        result["ios_evidence"]["command"] = ["true"]
        result["ios_evidence"]["destination"] = "unrelated simulator"
        self.write_json(self.result, result)
        self.write_json(self.ios_evidence_file, result["ios_evidence"])
        with self.assertRaisesRegex(validator.ValidationError, "retained helper result"):
            self.validate()

    def test_rejects_ios_object_that_differs_from_retained_helper_result(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        result = json.loads(self.result.read_text(encoding="utf-8"))
        result["ios_evidence"]["detail"] = "Substituted after the helper ran."
        self.write_json(self.result, result)
        with self.assertRaisesRegex(validator.ValidationError, "guard-owned manifest"):
            self.validate()

    def test_rejects_probe_that_did_not_run_on_both_surfaces(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        result = json.loads(self.result.read_text(encoding="utf-8"))
        content = "# Playtest Report: guidance\n\nSurface: terminal\nResult: PASS\n"
        probe = self.root / self.probe_paths[0]
        probe.write_text(content, encoding="utf-8")
        result["probe_evidence"][0]["content"] = content
        result["probe_evidence"][0]["sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_json(self.result, result)
        probe_manifest = json.loads(self.probe_manifest.read_text(encoding="utf-8"))
        probe_manifest["probes"][0]["report_content"] = content
        probe_manifest["probes"][0]["report_sha256"] = hashlib.sha256(
            content.encode()
        ).hexdigest()
        self.write_json(self.probe_manifest, probe_manifest)
        with self.assertRaisesRegex(validator.ValidationError, "not a both-surface route"):
            self.validate()

    def test_rejects_noop_that_ignores_a_failed_probe(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        result = json.loads(self.result.read_text(encoding="utf-8"))
        content = "# Playtest Report: guidance\n\nSurface: both\nResult: FAIL\n"
        probe = self.root / self.probe_paths[0]
        probe.write_text(content, encoding="utf-8")
        result["probe_evidence"][0]["content"] = content
        result["probe_evidence"][0]["sha256"] = hashlib.sha256(content.encode()).hexdigest()
        self.write_json(self.result, result)
        probe_manifest = json.loads(self.probe_manifest.read_text(encoding="utf-8"))
        probe_manifest["probes"][0]["report_content"] = content
        probe_manifest["probes"][0]["report_sha256"] = hashlib.sha256(
            content.encode()
        ).hexdigest()
        probe_manifest["probes"][0]["runner_returncode"] = 1
        self.write_json(self.probe_manifest, probe_manifest)
        with self.assertRaisesRegex(validator.ValidationError, "clean both-surface probes"):
            self.validate()

    def test_accepts_same_source_experiential_review(self) -> None:
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["previous_source_sha"] = self.source_sha
        manifest["review_kind"] = "experiential"
        self.write_json(self.manifest, manifest)
        self.write_result("noop")
        result = json.loads(self.result.read_text(encoding="utf-8"))
        result["previous_source_sha"] = self.source_sha
        result["review_kind"] = "experiential"
        self.write_json(self.result, result)
        self.write_json(self.findings, [])
        value = self.validate()
        self.assertEqual(value["review_kind"], "experiential")

    def test_rejects_intermediate_context_symlink(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        game_context = self.root / "reports/playtests/_context/game"
        shutil.rmtree(game_context)
        probe_context = self.root / "reports/probes"
        probe_context.mkdir(parents=True, exist_ok=True)
        game_context.symlink_to(probe_context, target_is_directory=True)
        with self.assertRaisesRegex(validator.ValidationError, "contains a symlink"):
            self.validate()

    def test_rejects_context_blob_that_differs_from_source(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])

        def fake_git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "HEAD"):
                return self.source_sha
            if args[0] in {"status", "cat-file"}:
                return ""
            if args[0] == "hash-object":
                return "staged-blob"
            if args[0] == "rev-parse":
                return "committed-blob"
            raise AssertionError(f"unexpected git call: {args}")

        with mock.patch.object(validator, "git", side_effect=fake_git):
            with self.assertRaisesRegex(validator.ValidationError, "differs from the claimed source"):
                validator.validate(
                    self.root,
                    "active",
                    self.source_sha,
                    self.manifest,
                    self.probe_manifest,
                    self.result,
                    self.findings,
                )

    def test_prepare_rejects_uncommitted_scenario(self) -> None:
        prepare_root = self.root / "prepare-root"
        scenario_root = prepare_root / "playtests/scenarios"
        scenario_root.mkdir(parents=True)
        (scenario_root / "committed.yaml").write_text("name: committed\n", encoding="utf-8")
        (scenario_root / "untracked.yaml").write_text("name: untracked\n", encoding="utf-8")

        def fake_git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "HEAD"):
                return self.source_sha
            if args[0] == "status":
                return ""
            if args[0] == "ls-tree":
                return "playtests/scenarios/committed.yaml"
            raise AssertionError(f"unexpected git call: {args}")

        with mock.patch.object(preparer, "git", side_effect=fake_git):
            with self.assertRaisesRegex(preparer.EvidenceError, "exactly match"):
                preparer.prepare(
                    prepare_root,
                    self.source_sha,
                    self.root / "prepare-manifest.json",
                )

    def test_prepare_rejects_committed_non_offline_scenario(self) -> None:
        prepare_root = self.root / "non-offline-root"
        scenario_root = prepare_root / "playtests/scenarios"
        scenario_root.mkdir(parents=True)
        scenario = scenario_root / "live.yaml"
        scenario.write_text(
            "name: live\nsurface: web\ncommands:\n  - look\noffline_ai: false\n",
            encoding="utf-8",
        )

        def fake_git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "HEAD"):
                return self.source_sha
            if args[0] == "status":
                return ""
            if args[0] == "ls-tree":
                return "playtests/scenarios/live.yaml"
            raise AssertionError(f"unexpected git call: {args}")

        with mock.patch.object(preparer, "git", side_effect=fake_git):
            with self.assertRaisesRegex(preparer.EvidenceError, "requires offline_ai: true"):
                preparer.prepare(
                    prepare_root,
                    self.source_sha,
                    self.root / "non-offline-manifest.json",
                )

    def test_prepare_scrubs_model_credentials_for_the_runner(self) -> None:
        prepare_root = self.root / "offline-root"
        scenario_root = prepare_root / "playtests/scenarios"
        scenario_root.mkdir(parents=True)
        (scenario_root / "offline.yaml").write_text(
            "name: offline\nsurface: web\ncommands:\n  - look\noffline_ai: true\n",
            encoding="utf-8",
        )
        for relative in preparer.CONTEXT_PATHS:
            context = prepare_root / relative
            context.parent.mkdir(parents=True, exist_ok=True)
            context.write_text("context\n", encoding="utf-8")

        def fake_git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "HEAD"):
                return self.source_sha
            if args[0] == "status":
                return ""
            if args[0] == "ls-tree":
                return "playtests/scenarios/offline.yaml"
            raise AssertionError(f"unexpected git call: {args}")

        def fake_run(command: list[str], cwd: Path, *, env=None):
            self.assertEqual(command[:3], [sys.executable, "-m", "tools.playtest_runner"])
            self.assertIsNotNone(env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("CABIN_LOCAL_OPENAI_API_KEY", env)
            report = prepare_root / "reports/playtests/offline.txt"
            report.parent.mkdir(parents=True)
            report.write_text("report\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "must-not-leak",
                "CABIN_LOCAL_OPENAI_API_KEY": "must-not-leak",
            },
        ):
            with mock.patch.object(preparer, "git", side_effect=fake_git):
                with mock.patch.object(preparer, "run", side_effect=fake_run):
                    with mock.patch.object(
                        preparer,
                        "prepare_ios_evidence",
                        return_value={"status": "unavailable"},
                    ):
                        manifest = preparer.prepare(
                            prepare_root,
                            self.source_sha,
                            self.root / "offline-manifest.json",
                        )
        self.assertEqual(manifest["runner_returncode"], 0)


if __name__ == "__main__":
    unittest.main()
