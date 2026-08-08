#!/usr/bin/env python3
"""Validate a bounded Cabin playtest review result before terminal action."""

from __future__ import annotations

import argparse
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
    ".agents/skills/the-cabin-playtest-review/scripts/validate_result.py",
)
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


def validate(
    root: Path,
    mode: str,
    source_sha: str,
    manifest_path: Path,
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
        "runner_returncode",
        "reports",
        "context",
    }
    if not isinstance(manifest, dict) or set(manifest) != manifest_keys:
        raise ValidationError("evidence manifest fields do not match schema v1")
    if manifest["schema_version"] != 1 or manifest["workflow"] != "cabin-playtest-review":
        raise ValidationError("evidence manifest schema or workflow is invalid")
    if manifest["source_sha"] != source_sha or manifest["runner_returncode"] not in {0, 1}:
        raise ValidationError("evidence manifest is not bound to this run")
    if not isinstance(manifest["reports"], list) or not manifest["reports"]:
        raise ValidationError("evidence manifest must list reports")
    if not isinstance(manifest["context"], list) or not manifest["context"]:
        raise ValidationError("evidence manifest must list staged context")
    if len(manifest["reports"]) != len(set(manifest["reports"])):
        raise ValidationError("evidence manifest contains duplicate reports")
    if len(manifest["context"]) != len(set(manifest["context"])):
        raise ValidationError("evidence manifest contains duplicate context paths")
    if tuple(manifest["context"]) != EXPECTED_CONTEXT:
        raise ValidationError("evidence manifest does not contain the exact context pack")
    for value in manifest["reports"]:
        validate_relative_file(root, value, "reports/playtests/")
    for value, source in zip(manifest["context"], CONTEXT_SOURCES, strict=True):
        staged = validate_relative_file(root, value, "reports/playtests/_context/")
        staged_blob = git(root, "hash-object", str(staged))
        committed_blob = git(root, "rev-parse", f"{source_sha}:{source}")
        if staged_blob != committed_blob:
            raise ValidationError(f"staged context differs from the claimed source: {source}")
    actual_reports = sorted(
        str(path.relative_to(root)) for path in (root / "reports/playtests").glob("*.txt")
    )
    if manifest["reports"] != actual_reports:
        raise ValidationError("evidence manifest does not match the generated report set")

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
        "outcome",
        "source_sha",
        "reviewed_reports",
        "probed_routes",
        "summary",
    }
    if not isinstance(result, dict) or set(result) != result_keys:
        raise ValidationError("result fields do not match schema v1")
    if result["schema_version"] != 1 or result["workflow"] != "cabin-playtest-review":
        raise ValidationError("result schema or workflow is invalid")
    if result["mode"] != mode or result["source_sha"] != source_sha:
        raise ValidationError("result mode or source SHA does not match the run")
    if result["outcome"] not in {"noop", "issues"}:
        raise ValidationError("result outcome must be noop or issues")
    if result["reviewed_reports"] != manifest["reports"]:
        raise ValidationError("reviewed_reports must exactly match the evidence manifest")
    if not isinstance(result["probed_routes"], list):
        raise ValidationError("probed_routes must be a list")
    if len(result["probed_routes"]) != len(set(result["probed_routes"])):
        raise ValidationError("probed_routes contains duplicates")
    for value in result["probed_routes"]:
        validate_relative_file(root, value, "reports/probes/")
    if not isinstance(result["summary"], str) or not result["summary"].strip() or len(result["summary"]) > 500:
        raise ValidationError("result summary must be 1 to 500 characters")
    if result["outcome"] == "noop" and findings:
        raise ValidationError("noop result requires an empty findings array")
    if result["outcome"] == "issues" and not findings:
        raise ValidationError("issues result requires at least one finding")

    return {
        "valid": True,
        "outcome": result["outcome"],
        "findings": len(findings),
        "reports": len(manifest["reports"]),
        "probes": len(result["probed_routes"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", required=True, choices=("shadow", "active"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--findings", required=True)
    args = parser.parse_args()
    try:
        value = validate(
            Path(args.root).expanduser().resolve(),
            args.mode,
            args.source_sha,
            Path(args.manifest).expanduser().resolve(),
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
