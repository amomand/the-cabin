from __future__ import annotations

import importlib.util
import json
import shutil
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
        self.write_json(
            self.manifest,
            {
                "schema_version": 1,
                "workflow": "cabin-playtest-review",
                "source_sha": self.source_sha,
                "runner_returncode": 0,
                "reports": ["reports/playtests/golden.txt"],
                "context": list(validator.EXPECTED_CONTEXT),
            },
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def write_result(self, outcome: str) -> None:
        self.write_json(
            self.result,
            {
                "schema_version": 1,
                "workflow": "cabin-playtest-review",
                "mode": "active",
                "outcome": outcome,
                "source_sha": self.source_sha,
                "reviewed_reports": ["reports/playtests/golden.txt"],
                "probed_routes": [],
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

    def test_rejects_intermediate_context_symlink(self) -> None:
        self.write_result("noop")
        self.write_json(self.findings, [])
        game_context = self.root / "reports/playtests/_context/game"
        shutil.rmtree(game_context)
        probe_context = self.root / "reports/probes"
        probe_context.mkdir(parents=True)
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


if __name__ == "__main__":
    unittest.main()
