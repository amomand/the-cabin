#!/usr/bin/env python3
"""Generate an exact-source deterministic evidence pack for Cabin review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
REPORT_ROOT = Path("reports/playtests")
CONTEXT_PATHS = (
    Path("game/story/anomalies.py"),
    Path("game/world_state.py"),
    Path("game/map.py"),
    Path("game/ai_interpreter.py"),
    Path("game/game_engine.py"),
    Path("docs/lore/plotline.md"),
    Path("docs/lore/the_lyer.md"),
    Path(".agents/skills/the-cabin-diegesis-review/SKILL.md"),
    Path(".agents/skills/the-cabin-continuity-review/SKILL.md"),
)
CHANGE_AREAS = ("ios", "engine", "story", "tests", "automation", "docs", "other")


class EvidenceError(RuntimeError):
    pass


def run(
    command: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git(root: Path, *args: str) -> str:
    completed = run(["git", *args], root)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise EvidenceError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def require_offline_scenarios(root: Path, scenario_paths: list[Path]) -> None:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tools.playtest_runner import load_scenario

    for path in scenario_paths:
        try:
            scenario = load_scenario(path)
        except (OSError, ValueError) as exc:
            raise EvidenceError(f"cannot read scenario {path.relative_to(root)}: {exc}") from exc
        if not scenario.offline_ai:
            raise EvidenceError(
                f"scheduled evidence requires offline_ai: true: {path.relative_to(root)}"
            )


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


def changed_paths(root: Path, previous_source_sha: str | None, source_sha: str) -> list[str]:
    if previous_source_sha is None or previous_source_sha == source_sha:
        return []
    if not re.fullmatch(r"[0-9a-f]{40}", previous_source_sha):
        raise EvidenceError("previous source SHA must be 40 lowercase hexadecimal characters")
    git(root, "cat-file", "-e", f"{previous_source_sha}^{{commit}}")
    return sorted(
        path
        for path in git(
            root,
            "diff",
            "--name-only",
            previous_source_sha,
            source_sha,
        ).splitlines()
        if path
    )


def prepare(
    root: Path,
    source_sha: str,
    manifest_path: Path,
    previous_source_sha: str | None = None,
) -> dict[str, object]:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != source_sha:
        raise EvidenceError("worktree HEAD does not match the claimed source")
    if git(root, "status", "--porcelain"):
        raise EvidenceError("worktree must be clean before evidence generation")

    report_root = root / REPORT_ROOT
    if report_root.exists() and any(report_root.iterdir()):
        raise EvidenceError("reports/playtests already contains evidence")

    scenario_paths = sorted((root / "playtests/scenarios").glob("*.yaml"))
    if not scenario_paths:
        raise EvidenceError("no playtest scenarios found")
    committed_scenarios = sorted(
        path
        for path in git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            source_sha,
            "--",
            "playtests/scenarios",
        ).splitlines()
        if path.endswith(".yaml")
    )
    worktree_scenarios = [str(path.relative_to(root)) for path in scenario_paths]
    if worktree_scenarios != committed_scenarios:
        raise EvidenceError("playtest scenarios do not exactly match the claimed source")

    require_offline_scenarios(root, scenario_paths)

    runner_env = os.environ.copy()
    runner_env.pop("OPENAI_API_KEY", None)
    runner_env.pop("CABIN_LOCAL_OPENAI_API_KEY", None)

    completed = run(
        [sys.executable, "-m", "tools.playtest_runner", "--report-dir", str(report_root)],
        root,
        env=runner_env,
    )
    if completed.returncode not in {0, 1}:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise EvidenceError(f"playtest runner could not produce evidence: {detail}")

    reports = sorted(report_root.glob("*.txt"))
    if len(reports) != len(scenario_paths):
        raise EvidenceError(
            f"expected {len(scenario_paths)} reports, found {len(reports)}"
        )

    staged: list[Path] = []
    context_root = report_root / "_context"
    for relative in CONTEXT_PATHS:
        source = root / relative
        if not source.is_file():
            raise EvidenceError(f"required context file is missing: {relative}")
        destination = context_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        staged.append(destination)

    if git(root, "status", "--porcelain"):
        raise EvidenceError("evidence preparation left unexpected worktree changes")

    paths = changed_paths(root, previous_source_sha, source_sha)
    area_counts = {area: 0 for area in CHANGE_AREAS}
    for path in paths:
        area_counts[change_area(path)] += 1

    manifest = {
        "schema_version": 2,
        "workflow": "cabin-playtest-review",
        "source_sha": source_sha,
        "previous_source_sha": previous_source_sha,
        "review_kind": (
            "experiential" if previous_source_sha == source_sha else "regression"
        ),
        "changed_paths": paths,
        "change_areas": area_counts,
        "runner_returncode": completed.returncode,
        "reports": [str(path.relative_to(root)) for path in reports],
        "report_sha256": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in reports
        },
        "report_contents": {
            str(path.relative_to(root)): path.read_text(encoding="utf-8")
            for path in reports
        },
        "context": [str(path.relative_to(root)) for path in staged],
        "context_sha256": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in staged
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--previous-source-sha")
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        root = Path(args.root).expanduser().resolve()
        manifest = Path(args.manifest).expanduser().resolve()
        value = prepare(root, args.source_sha, manifest, args.previous_source_sha)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (EvidenceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
