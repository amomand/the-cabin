#!/usr/bin/env python3
"""Run two reviewer-chosen offline both-surface probes and retain their evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
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


class ProbeError(RuntimeError):
    pass


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
        raise ProbeError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def parse_probe(value: str) -> tuple[str, Path]:
    family, separator, raw_path = value.partition("=")
    if not separator or family not in PROBE_FAMILIES or not raw_path:
        raise ProbeError("each probe must be FAMILY=/absolute/scenario.yaml")
    path = Path(raw_path).expanduser()
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ProbeError(f"probe scenario is missing or unsafe: {raw_path}")
    return family, path.resolve()


def prepare(
    root: Path,
    source_sha: str,
    probe_values: list[str],
    manifest_path: Path,
) -> dict[str, object]:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != source_sha:
        raise ProbeError("worktree HEAD does not match the claimed source")
    if git(root, "status", "--porcelain"):
        raise ProbeError("worktree must be clean before probe generation")
    if len(probe_values) != 2:
        raise ProbeError("exactly two probes are required")
    probes = [parse_probe(value) for value in probe_values]
    families = [family for family, _ in probes]
    paths = [path for _, path in probes]
    if len(set(families)) != 2 or len(set(paths)) != 2:
        raise ProbeError("probe families and scenario paths must be unique")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tools.playtest_runner import load_scenario, run_scenario, write_report

    report_dir = root / "reports/probes"
    if report_dir.exists() and any(report_dir.iterdir()):
        raise ProbeError("reports/probes already contains evidence")
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("CABIN_LOCAL_OPENAI_API_KEY", None)
    records: list[dict[str, object]] = []
    scenario_names: set[str] = set()
    for family, path in probes:
        try:
            scenario = load_scenario(path)
        except (OSError, ValueError) as exc:
            raise ProbeError(f"cannot load probe {path}: {exc}") from exc
        if not scenario.offline_ai or scenario.surface != "both":
            raise ProbeError(f"probe must use offline_ai: true and surface: both: {path}")
        if scenario.name in scenario_names:
            raise ProbeError("probe scenario names must be unique")
        scenario_names.add(scenario.name)
        result = run_scenario(scenario)
        report = write_report(result, report_dir)
        relative = str(report.relative_to(root))
        records.append(
            {
                "family": family,
                "scenario_name": scenario.name,
                "scenario_path": str(path),
                "scenario_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "scenario_content": path.read_text(encoding="utf-8"),
                "runner_returncode": 0 if result.passed else 1,
                "report_path": relative,
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "report_content": report.read_text(encoding="utf-8"),
            }
        )
    if git(root, "status", "--porcelain"):
        raise ProbeError("probe generation left unexpected worktree changes")
    manifest = {
        "schema_version": 1,
        "workflow": "cabin-playtest-review",
        "source_sha": source_sha,
        "probes": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--probe", action="append", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        value = prepare(
            Path(args.root).expanduser(),
            args.source_sha,
            args.probe,
            Path(args.manifest).expanduser(),
        )
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (ProbeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
