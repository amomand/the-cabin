#!/usr/bin/env python3
"""Atomically append one completed Cabin review to its probe-rotation history."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoryError(RuntimeError):
    pass


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoryError(f"cannot read {label} from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HistoryError(f"{label} must be a JSON object")
    return value


def parse_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryError("recorded-at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise HistoryError("recorded-at must include a timezone")
    return parsed.isoformat()


def validate_urls(values: list[str]) -> list[str]:
    pattern = re.compile(r"^https://github\.com/amomand/the-cabin/issues/\d+$")
    if len(values) != len(set(values)) or any(not pattern.fullmatch(value) for value in values):
        raise HistoryError("issue URLs must be unique The Cabin issue URLs")
    return values


def append_history(
    history_path: Path,
    run_id: str,
    recorded_at: str,
    manifest_path: Path,
    result_path: Path,
    issue_urls: list[str],
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", run_id):
        raise HistoryError("run ID is not a safe bounded identifier")
    manifest_path = manifest_path.resolve()
    result_path = result_path.resolve()
    manifest = load_object(manifest_path, "manifest")
    result = load_object(result_path, "result")
    if manifest.get("schema_version") != 2 or result.get("schema_version") != 2:
        raise HistoryError("coverage history requires schema-v2 evidence")
    for key in ("source_sha", "previous_source_sha", "review_kind"):
        if result.get(key) != manifest.get(key):
            raise HistoryError(f"result {key} does not match the manifest")
    outcome = result.get("outcome")
    if outcome not in {"noop", "coverage-gap", "issues"}:
        raise HistoryError("result outcome is not a successful review outcome")
    if (outcome == "issues") != bool(issue_urls):
        raise HistoryError("issue URLs must be present exactly for an issues outcome")
    routes = result.get("probed_routes")
    families = result.get("probe_families")
    ios_evidence = result.get("ios_evidence")
    if not isinstance(routes, list) or not all(isinstance(value, str) for value in routes):
        raise HistoryError("result probed_routes is invalid")
    if not isinstance(families, list) or len(families) != len(routes):
        raise HistoryError("result probe_families is invalid")
    if not isinstance(ios_evidence, dict) or ios_evidence.get("status") not in {
        "passed",
        "failed",
        "unavailable",
    }:
        raise HistoryError("result ios_evidence is invalid")

    history_path = history_path.expanduser().resolve()
    if history_path.exists():
        history = load_object(history_path, "coverage history")
    else:
        history = {"schema_version": 1, "runs": []}
    if set(history) != {"schema_version", "runs"} or history["schema_version"] != 1:
        raise HistoryError("coverage history schema is invalid")
    runs = history["runs"]
    if not isinstance(runs, list) or any(not isinstance(value, dict) for value in runs):
        raise HistoryError("coverage history runs must be a JSON array")
    if any(value.get("run_id") == run_id for value in runs):
        raise HistoryError(f"coverage history already contains run {run_id}")

    record = {
        "run_id": run_id,
        "recorded_at": parse_time(recorded_at),
        "review_kind": result["review_kind"],
        "source_sha": result["source_sha"],
        "previous_source_sha": result["previous_source_sha"],
        "probed_routes": routes,
        "probe_families": families,
        "terminal_web_status": result.get("terminal_web_status"),
        "ios_status": ios_evidence["status"],
        "outcome": outcome,
        "issue_urls": validate_urls(issue_urls),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "evidence_path": str(manifest_path.parent),
    }
    runs.append(record)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{history_path.name}.",
        dir=history_path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(history_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--issue-url", action="append", default=[])
    args = parser.parse_args()
    try:
        record = append_history(
            Path(args.history),
            args.run_id,
            args.recorded_at,
            Path(args.manifest),
            Path(args.result),
            args.issue_url,
        )
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    except (HistoryError, OSError) as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
