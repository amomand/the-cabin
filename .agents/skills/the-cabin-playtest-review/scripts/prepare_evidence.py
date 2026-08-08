#!/usr/bin/env python3
"""Generate an exact-source deterministic evidence pack for Cabin review."""

from __future__ import annotations

import argparse
import json
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


class EvidenceError(RuntimeError):
    pass


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
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


def prepare(root: Path, source_sha: str, manifest_path: Path) -> dict[str, object]:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != source_sha:
        raise EvidenceError("worktree HEAD does not match the claimed source")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise EvidenceError("tracked worktree must be clean before evidence generation")

    report_root = root / REPORT_ROOT
    if report_root.exists() and any(report_root.iterdir()):
        raise EvidenceError("reports/playtests already contains evidence")

    scenario_paths = sorted((root / "playtests/scenarios").glob("*.yaml"))
    if not scenario_paths:
        raise EvidenceError("no playtest scenarios found")

    completed = run(
        [sys.executable, "-m", "tools.playtest_runner", "--report-dir", str(report_root)],
        root,
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

    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise EvidenceError("evidence preparation changed tracked files")

    manifest = {
        "schema_version": 1,
        "workflow": "cabin-playtest-review",
        "source_sha": source_sha,
        "runner_returncode": completed.returncode,
        "reports": [str(path.relative_to(root)) for path in reports],
        "context": [str(path.relative_to(root)) for path in staged],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        root = Path(args.root).expanduser().resolve()
        manifest = Path(args.manifest).expanduser().resolve()
        value = prepare(root, args.source_sha, manifest)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (EvidenceError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
