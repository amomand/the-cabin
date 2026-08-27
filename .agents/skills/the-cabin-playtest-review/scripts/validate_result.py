#!/usr/bin/env python3
"""Validate a bounded Cabin playtest review result before terminal action."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
SEVERITIES = {"diegesis", "continuity", "balance", "bug"}
BODY_HEADINGS = (
    "## What's wrong",
    "## Evidence",
    "## Why it matters",
    "## Reproduction",
)
TRUSTED_PATHS = (
    ".agents/skills/the-cabin-playtest-review/SKILL.md",
    ".agents/skills/the-cabin-playtest-review/scripts/prepare_evidence.py",
    ".agents/skills/the-cabin-playtest-review/scripts/prepare_probes.py",
    ".agents/skills/the-cabin-playtest-review/scripts/record_coverage.py",
    ".agents/skills/the-cabin-playtest-review/scripts/run_ios_lane.py",
    ".agents/skills/the-cabin-playtest-review/scripts/validate_result.py",
)
CHANGE_AREAS = ("ios", "engine", "story", "tests", "automation", "docs", "other")
PROBE_FAMILIES = {
    "ending",
    "free-text",
    "guidance",
    "movement",
    "save-load",
    "state-consequence",
    "story-transition",
    "surface-parity",
    "utility",
}
UNCOVERED_AREAS = {"ios-device", "ios-simulator", "live-model"}
IOS_DESTINATION = "iPhone Air"
CONTEXT_SOURCES = (
    "game/story/anomalies.py",
    "game/world_state.py",
    "game/map.py",
    "game/ai_interpreter.py",
    "game/game_engine.py",
    "docs/lore/plotline.md",
    "docs/lore/the_lyer.md",
    ".agents/skills/the-cabin-diegesis-review/SKILL.md",
    ".agents/skills/the-cabin-continuity-review/SKILL.md",
)
EXPECTED_CONTEXT = tuple(
    f"reports/playtests/_context/{path}" for path in CONTEXT_SOURCES
)


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON from {path}: {exc}") from exc


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ValidationError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def validate_relative_file(root: Path, value: str, prefix: str) -> Path:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValidationError(f"evidence path must start with {prefix}: {value!r}")
    candidate = root / value
    component = root
    for part in Path(value).parts:
        component /= part
        if component.is_symlink():
            raise ValidationError(f"evidence path contains a symlink: {value}")
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"evidence path escapes the worktree: {value}") from exc
    if not path.is_file():
        raise ValidationError(f"evidence file is missing or unsafe: {value}")
    return path


def validate_finding(finding: Any) -> None:
    expected = {"title", "body", "severity", "evidence", "reproduction"}
    if not isinstance(finding, dict) or set(finding) != expected:
        raise ValidationError("each finding must contain exactly the required fields")
    if any(not isinstance(finding[key], str) or not finding[key].strip() for key in expected):
        raise ValidationError("finding fields must be non-empty strings")
    if finding["severity"] not in SEVERITIES:
        raise ValidationError(f"invalid finding severity: {finding['severity']!r}")
    if finding["title"].startswith("[playtest]"):
        raise ValidationError("finding title must not include the publisher prefix")
    if len(finding["title"]) > 120:
        raise ValidationError("finding title exceeds 120 characters")
    body = finding["body"]
    positions = [body.find(heading) for heading in BODY_HEADINGS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValidationError("finding body headings are missing or out of order")
    if finding["evidence"] not in body:
        raise ValidationError("finding evidence must appear verbatim in the issue body")
    if finding["reproduction"] not in body:
        raise ValidationError("finding reproduction must appear verbatim in the issue body")
    if "<!-- local-agentic-control:" in body:
        raise ValidationError("finding body contains a reserved control marker")


def change_area(path: str) -> str:
    if path.startswith("ios/"):
        return "ios"
    if path.startswith(("game/", "server/")) or path in {
        "main.py",
        "config.json.example",
    }:
        return "engine"
    if path.startswith(("docs/lore/", "stories/", "playtests/scenarios/")):
        return "story"
    if path.startswith("tests/"):
        return "tests"
    if path.startswith((".agents/", ".claude/", ".github/")):
        return "automation"
    if path.startswith("docs/") or path in {"AGENTS.md", "CONTRIBUTING.md", "README.md"}:
        return "docs"
    return "other"


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValidationError(f"{label} is not a SHA-256 digest")
    return value


def validate_ios_evidence(value: Any) -> dict[str, Any]:
    expected = {
        "schema_version",
        "status",
        "command",
        "destination",
        "detail",
        "runtime_source",
        "log_path",
        "log_sha256",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValidationError("ios_evidence fields do not match schema v1")
    if value["schema_version"] != 1 or value["status"] not in {
        "passed",
        "failed",
        "unavailable",
    }:
        raise ValidationError("ios_evidence schema or status is invalid")
    if not isinstance(value["command"], list) or any(
        not isinstance(part, str) or not part for part in value["command"]
    ):
        raise ValidationError("ios_evidence command must be a list of strings")
    for key in ("destination", "detail"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValidationError(f"ios_evidence {key} must be a non-empty string")
    if value["destination"] != IOS_DESTINATION:
        raise ValidationError(f"ios_evidence destination must be {IOS_DESTINATION}")
    if value["runtime_source"] is not None and value["runtime_source"] not in {
        "compatible-cache",
        "fresh-prepare",
        "in-place-cache",
    }:
        raise ValidationError("ios_evidence runtime_source is invalid")
    if not isinstance(value["log_path"], str):
        raise ValidationError("ios_evidence log_path must be a string")
    log_path = Path(value["log_path"])
    if not log_path.is_absolute() or log_path.is_symlink() or not log_path.is_file():
        raise ValidationError("ios_evidence log is missing or unsafe")
    expected_hash = validate_sha256(value["log_sha256"], "ios_evidence log hash")
    if hashlib.sha256(log_path.read_bytes()).hexdigest() != expected_hash:
        raise ValidationError("ios_evidence log differs from its recorded hash")
    evidence_path = log_path.parent / "ios-evidence.json"
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ValidationError("retained ios-evidence.json is missing or unsafe")
    if load_json(evidence_path) != value:
        raise ValidationError("ios_evidence differs from the retained helper result")
    if value["status"] == "unavailable":
        if value["command"]:
            raise ValidationError("unavailable ios_evidence cannot claim an executed command")
        return value
    destination_id = value["command"][7] if len(value["command"]) == 12 else ""
    expected_command = [
        "xcodebuild",
        "test",
        "-project",
        "ios/TheCabin.xcodeproj",
        "-scheme",
        "TheCabin",
        "-destination",
        destination_id,
        "-derivedDataPath",
        str(log_path.parent / "DerivedData"),
        "-resultBundlePath",
        str(log_path.parent / "TheCabinTests.xcresult"),
    ]
    if (
        value["command"] != expected_command
        or not re.fullmatch(r"id=[0-9A-F-]{36}", destination_id)
        or value["runtime_source"] is None
    ):
        raise ValidationError("executed ios_evidence is not the required full XCTest command")
    if value["status"] == "passed":
        if "** TEST SUCCEEDED **" not in log_path.read_text(encoding="utf-8"):
            raise ValidationError("passed ios_evidence lacks xcodebuild success output")
        if not (log_path.parent / "TheCabinTests.xcresult").is_dir():
            raise ValidationError("passed ios_evidence lacks the retained result bundle")
    return value


def validate(
    root: Path,
    mode: str,
    source_sha: str,
    manifest_path: Path,
    probe_manifest_path: Path,
    result_path: Path,
    findings_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    if mode not in {"shadow", "active"}:
        raise ValidationError("mode must be shadow or active")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValidationError("source SHA must be 40 lowercase hexadecimal characters")
    if git(root, "rev-parse", "HEAD") != source_sha:
        raise ValidationError("worktree HEAD does not match the claimed source")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValidationError("tracked worktree differs from the claimed source")
    for path in TRUSTED_PATHS:
        git(root, "cat-file", "-e", f"{source_sha}:{path}")

    manifest = load_json(manifest_path)
    manifest_keys = {
        "schema_version",
        "workflow",
        "source_sha",
        "previous_source_sha",
        "review_kind",
        "changed_paths",
        "change_areas",
        "runner_returncode",
        "reports",
        "report_sha256",
        "report_contents",
        "context",
        "context_sha256",
        "ios_evidence",
    }
    if not isinstance(manifest, dict) or set(manifest) != manifest_keys:
        raise ValidationError("evidence manifest fields do not match schema v2")
    if manifest["schema_version"] != 2 or manifest["workflow"] != "cabin-playtest-review":
        raise ValidationError("evidence manifest schema or workflow is invalid")
    if manifest["source_sha"] != source_sha or manifest["runner_returncode"] not in {0, 1}:
        raise ValidationError("evidence manifest is not bound to this run")
    previous_source_sha = manifest["previous_source_sha"]
    if previous_source_sha is not None and not (
        isinstance(previous_source_sha, str)
        and re.fullmatch(r"[0-9a-f]{40}", previous_source_sha)
    ):
        raise ValidationError("previous_source_sha must be null or a full SHA")
    expected_kind = "experiential" if previous_source_sha == source_sha else "regression"
    if manifest["review_kind"] != expected_kind:
        raise ValidationError("review_kind does not match the source transition")
    changed_paths = manifest["changed_paths"]
    if not isinstance(changed_paths, list) or changed_paths != sorted(set(changed_paths)):
        raise ValidationError("changed_paths must be a sorted unique list")
    if any(
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        for path in changed_paths
    ):
        raise ValidationError("changed_paths contains an unsafe path")
    if expected_kind == "experiential" and changed_paths:
        raise ValidationError("experiential reviews cannot report changed paths")
    if not isinstance(manifest["change_areas"], dict) or set(manifest["change_areas"]) != set(
        CHANGE_AREAS
    ):
        raise ValidationError("change_areas does not match the required categories")
    expected_areas = {area: 0 for area in CHANGE_AREAS}
    for path in changed_paths:
        expected_areas[change_area(path)] += 1
    if manifest["change_areas"] != expected_areas:
        raise ValidationError("change_areas does not match changed_paths")
    if not isinstance(manifest["reports"], list) or not manifest["reports"]:
        raise ValidationError("evidence manifest must list reports")
    if not isinstance(manifest["report_sha256"], dict):
        raise ValidationError("evidence manifest must bind report hashes")
    if not isinstance(manifest["report_contents"], dict):
        raise ValidationError("evidence manifest must retain report contents")
    if not isinstance(manifest["context"], list) or not manifest["context"]:
        raise ValidationError("evidence manifest must list staged context")
    if len(manifest["reports"]) != len(set(manifest["reports"])):
        raise ValidationError("evidence manifest contains duplicate reports")
    if len(manifest["context"]) != len(set(manifest["context"])):
        raise ValidationError("evidence manifest contains duplicate context paths")
    if tuple(manifest["context"]) != EXPECTED_CONTEXT:
        raise ValidationError("evidence manifest does not contain the exact context pack")
    if set(manifest["report_sha256"]) != set(manifest["reports"]):
        raise ValidationError("report hashes do not exactly match the report set")
    if set(manifest["report_contents"]) != set(manifest["reports"]):
        raise ValidationError("report contents do not exactly match the report set")
    for value in manifest["reports"]:
        report = validate_relative_file(root, value, "reports/playtests/")
        expected_hash = validate_sha256(manifest["report_sha256"][value], f"report hash: {value}")
        if hashlib.sha256(report.read_bytes()).hexdigest() != expected_hash:
            raise ValidationError(f"report content differs from the evidence manifest: {value}")
        if manifest["report_contents"][value] != report.read_text(encoding="utf-8"):
            raise ValidationError(f"retained report content differs from the evidence file: {value}")
    if not isinstance(manifest["context_sha256"], dict) or set(
        manifest["context_sha256"]
    ) != set(manifest["context"]):
        raise ValidationError("context hashes do not exactly match the context set")
    for value, source in zip(manifest["context"], CONTEXT_SOURCES, strict=True):
        staged = validate_relative_file(root, value, "reports/playtests/_context/")
        expected_hash = validate_sha256(manifest["context_sha256"][value], f"context hash: {value}")
        if hashlib.sha256(staged.read_bytes()).hexdigest() != expected_hash:
            raise ValidationError(f"staged context differs from its recorded hash: {source}")
        staged_blob = git(root, "hash-object", str(staged))
        committed_blob = git(root, "rev-parse", f"{source_sha}:{source}")
        if staged_blob != committed_blob:
            raise ValidationError(f"staged context differs from the claimed source: {source}")
    actual_reports = sorted(
        str(path.relative_to(root)) for path in (root / "reports/playtests").glob("*.txt")
    )
    if manifest["reports"] != actual_reports:
        raise ValidationError("evidence manifest does not match the generated report set")
    anchored_ios_evidence = validate_ios_evidence(manifest["ios_evidence"])

    probe_manifest = load_json(probe_manifest_path)
    if not isinstance(probe_manifest, dict) or set(probe_manifest) != {
        "schema_version",
        "workflow",
        "source_sha",
        "probes",
    }:
        raise ValidationError("probe manifest fields do not match schema v1")
    if (
        probe_manifest["schema_version"] != 1
        or probe_manifest["workflow"] != "cabin-playtest-review"
        or probe_manifest["source_sha"] != source_sha
    ):
        raise ValidationError("probe manifest is not bound to this run")
    probes = probe_manifest["probes"]
    if not isinstance(probes, list) or len(probes) != 2:
        raise ValidationError("probe manifest must contain exactly two probes")
    manifest_routes: list[str] = []
    manifest_families: list[str] = []
    manifest_probe_evidence: list[dict[str, str]] = []
    probe_returncodes: list[int] = []
    for probe in probes:
        expected_probe_keys = {
            "family",
            "scenario_name",
            "scenario_path",
            "scenario_sha256",
            "scenario_content",
            "runner_returncode",
            "report_path",
            "report_sha256",
            "report_content",
        }
        if not isinstance(probe, dict) or set(probe) != expected_probe_keys:
            raise ValidationError("probe manifest entry fields are invalid")
        family = probe["family"]
        if family not in PROBE_FAMILIES:
            raise ValidationError("probe manifest contains an unknown family")
        if not isinstance(probe["scenario_name"], str) or not probe["scenario_name"].strip():
            raise ValidationError("probe scenario name is invalid")
        if not isinstance(probe["scenario_path"], str):
            raise ValidationError("probe scenario path is invalid")
        scenario_path = Path(probe["scenario_path"])
        if not scenario_path.is_absolute() or scenario_path.is_symlink() or not scenario_path.is_file():
            raise ValidationError("probe scenario is missing or unsafe")
        scenario_content = probe["scenario_content"]
        if not isinstance(scenario_content, str) or scenario_content != scenario_path.read_text(
            encoding="utf-8"
        ):
            raise ValidationError("probe scenario differs from its retained content")
        if hashlib.sha256(scenario_path.read_bytes()).hexdigest() != validate_sha256(
            probe["scenario_sha256"], "probe scenario hash"
        ):
            raise ValidationError("probe scenario differs from its recorded hash")
        report_path = probe["report_path"]
        report = validate_relative_file(root, report_path, "reports/probes/")
        report_content = probe["report_content"]
        if not isinstance(report_content, str) or report_content != report.read_text(
            encoding="utf-8"
        ):
            raise ValidationError("probe report differs from its retained content")
        report_hash = validate_sha256(probe["report_sha256"], "probe report hash")
        if hashlib.sha256(report.read_bytes()).hexdigest() != report_hash:
            raise ValidationError("probe report differs from its recorded hash")
        if not re.search(r"^Surface: both$", report_content, flags=re.MULTILINE):
            raise ValidationError("guarded probe report is not a both-surface route")
        if type(probe["runner_returncode"]) is not int or probe["runner_returncode"] not in {
            0,
            1,
        }:
            raise ValidationError("probe runner return code is invalid")
        manifest_routes.append(report_path)
        manifest_families.append(family)
        manifest_probe_evidence.append(
            {"path": report_path, "sha256": report_hash, "content": report_content}
        )
        probe_returncodes.append(probe["runner_returncode"])
    if len(set(manifest_routes)) != 2 or len(set(manifest_families)) != 2:
        raise ValidationError("probe manifest routes and families must be unique")

    findings = load_json(findings_path)
    if not isinstance(findings, list) or len(findings) > 3:
        raise ValidationError("findings must be a JSON array containing at most three items")
    for finding in findings:
        validate_finding(finding)
    normalised_titles = [finding["title"].strip().casefold() for finding in findings]
    if len(normalised_titles) != len(set(normalised_titles)):
        raise ValidationError("findings contain duplicate titles")

    result = load_json(result_path)
    result_keys = {
        "schema_version",
        "workflow",
        "mode",
        "review_kind",
        "outcome",
        "source_sha",
        "previous_source_sha",
        "reviewed_reports",
        "probed_routes",
        "probe_evidence",
        "probe_families",
        "terminal_web_status",
        "ios_evidence",
        "live_model_status",
        "uncovered_areas",
        "summary",
    }
    if not isinstance(result, dict) or set(result) != result_keys:
        raise ValidationError("result fields do not match schema v2")
    if result["schema_version"] != 2 or result["workflow"] != "cabin-playtest-review":
        raise ValidationError("result schema or workflow is invalid")
    if (
        result["mode"] != mode
        or result["source_sha"] != source_sha
        or result["previous_source_sha"] != previous_source_sha
        or result["review_kind"] != manifest["review_kind"]
    ):
        raise ValidationError("result mode or source SHA does not match the run")
    if result["outcome"] not in {"noop", "issues", "coverage-gap"}:
        raise ValidationError("result outcome must be noop, issues or coverage-gap")
    if result["reviewed_reports"] != manifest["reports"]:
        raise ValidationError("reviewed_reports must exactly match the evidence manifest")
    probed_routes = result["probed_routes"]
    if not isinstance(probed_routes, list) or len(probed_routes) != 2:
        raise ValidationError("probed_routes must contain exactly two routes")
    if len(probed_routes) != len(set(probed_routes)):
        raise ValidationError("probed_routes contains duplicates")
    probe_evidence = result["probe_evidence"]
    if not isinstance(probe_evidence, list) or len(probe_evidence) != len(probed_routes):
        raise ValidationError("probe_evidence must match the probed route count")
    evidence_paths: list[str] = []
    for evidence in probe_evidence:
        if not isinstance(evidence, dict) or set(evidence) != {"path", "sha256", "content"}:
            raise ValidationError("probe_evidence entries have invalid fields")
        path = evidence["path"]
        report = validate_relative_file(root, path, "reports/probes/")
        digest = validate_sha256(evidence["sha256"], f"probe hash: {path}")
        content = evidence["content"]
        if not isinstance(content, str) or content != report.read_text(encoding="utf-8"):
            raise ValidationError(f"retained probe content differs from the evidence file: {path}")
        if hashlib.sha256(report.read_bytes()).hexdigest() != digest:
            raise ValidationError(f"probe report differs from its recorded hash: {path}")
        if not re.search(r"^Surface: both$", content, flags=re.MULTILINE):
            raise ValidationError(f"probe report is not a both-surface route: {path}")
        evidence_paths.append(path)
    if evidence_paths != probed_routes:
        raise ValidationError("probe_evidence order must match probed_routes")
    if probed_routes != manifest_routes or probe_evidence != manifest_probe_evidence:
        raise ValidationError("result probes do not match the guard-owned probe manifest")
    probe_families = result["probe_families"]
    if (
        not isinstance(probe_families, list)
        or len(probe_families) != len(probed_routes)
        or len(probe_families) != len(set(probe_families))
        or any(family not in PROBE_FAMILIES for family in probe_families)
    ):
        raise ValidationError("probe_families must be unique recognised families")
    if probe_families != manifest_families:
        raise ValidationError("probe_families do not match the guard-owned probe manifest")
    expected_terminal_status = "passed" if manifest["runner_returncode"] == 0 else "failed"
    if result["terminal_web_status"] != expected_terminal_status:
        raise ValidationError("terminal_web_status does not match the evidence runner")
    if result["ios_evidence"] != anchored_ios_evidence:
        raise ValidationError("result ios_evidence does not match the guard-owned manifest")
    ios_evidence = result["ios_evidence"]
    if result["live_model_status"] != "not-run":
        raise ValidationError("scheduled review must record live_model_status as not-run")
    uncovered = result["uncovered_areas"]
    if (
        not isinstance(uncovered, list)
        or uncovered != sorted(set(uncovered))
        or any(area not in UNCOVERED_AREAS for area in uncovered)
        or not {"ios-device", "live-model"} <= set(uncovered)
    ):
        raise ValidationError("uncovered_areas must retain the device and live-model boundaries")
    if ios_evidence["status"] == "passed" and "ios-simulator" in uncovered:
        raise ValidationError("a passed iOS lane cannot leave ios-simulator uncovered")
    if ios_evidence["status"] != "passed" and "ios-simulator" not in uncovered:
        raise ValidationError("an incomplete iOS lane must leave ios-simulator uncovered")
    if not isinstance(result["summary"], str) or not result["summary"].strip() or len(result["summary"]) > 1000:
        raise ValidationError("result summary must be 1 to 1000 characters")
    if result["outcome"] == "noop" and findings:
        raise ValidationError("noop result requires an empty findings array")
    if result["outcome"] == "coverage-gap" and findings:
        raise ValidationError("coverage-gap result requires an empty findings array")
    if result["outcome"] == "issues" and not findings:
        raise ValidationError("issues result requires at least one finding")
    lanes_clean = manifest["runner_returncode"] == 0 and ios_evidence["status"] == "passed"
    if result["outcome"] == "noop" and not lanes_clean:
        raise ValidationError("noop requires clean terminal/web and iOS simulator lanes")
    if result["outcome"] == "coverage-gap" and lanes_clean:
        raise ValidationError("coverage-gap requires an incomplete evidence lane")
    if result["outcome"] in {"noop", "coverage-gap"} and any(
        value != 0 for value in probe_returncodes
    ):
        raise ValidationError("a no-finding outcome requires clean both-surface probes")

    return {
        "valid": True,
        "review_kind": result["review_kind"],
        "outcome": result["outcome"],
        "findings": len(findings),
        "reports": len(manifest["reports"]),
        "probes": len(result["probed_routes"]),
        "ios_status": ios_evidence["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", required=True, choices=("shadow", "active"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--probe-manifest", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--findings", required=True)
    args = parser.parse_args()
    try:
        value = validate(
            Path(args.root).expanduser().resolve(),
            args.mode,
            args.source_sha,
            Path(args.manifest).expanduser().resolve(),
            Path(args.probe_manifest).expanduser().resolve(),
            Path(args.result).expanduser().resolve(),
            Path(args.findings).expanduser().resolve(),
        )
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (ValidationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
