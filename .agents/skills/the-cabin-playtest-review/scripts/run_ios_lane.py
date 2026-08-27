#!/usr/bin/env python3
"""Run the exact-source iOS simulator evidence lane without model credentials."""

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
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE = Path("/Users/alexomand/repos/the-cabin/ios/EmbeddedPython")
EXPECTED_PREPARED_LINES = {
    "Python Apple Support: 3.13-b14",
    "Archive SHA256: 8b5cb76ef8d8a2946052479358eeec9d54b4496cb60920e175ec1489b5cf7963",
    "Model transport: direct-httpx (no OpenAI SDK or pydantic-core)",
}


class IOSLaneError(RuntimeError):
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
        stderr=subprocess.STDOUT,
        check=False,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatible_cache(root: Path, cache: Path) -> bool:
    prepared = cache / "PREPARED.txt"
    framework = cache / "Python.xcframework/Info.plist"
    packages = cache / "app_packages"
    if not prepared.is_file() or not framework.is_file() or not packages.is_dir():
        return False
    lines = set(prepared.read_text(encoding="utf-8").splitlines())
    if not EXPECTED_PREPARED_LINES <= lines:
        return False
    source_requirements = cache.parent / "requirements-ios.txt"
    target_requirements = root / "ios/requirements-ios.txt"
    if not source_requirements.is_file() or not target_requirements.is_file():
        return False
    return sha256(source_requirements) == sha256(target_requirements)


def copy_cached_runtime(cache: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name in ("Python.xcframework", "app_packages"):
        destination = target / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(cache / name, destination, symlinks=True)
    shutil.copy2(cache / "PREPARED.txt", target / "PREPARED.txt")


def prepare_runtime(root: Path, cache: Path, env: dict[str, str]) -> str:
    target = root / "ios/EmbeddedPython"
    if compatible_cache(root, cache):
        if cache.resolve() != target.resolve():
            copy_cached_runtime(cache, target)
        refreshed = run(["./scripts/refresh_embedded_sources.sh"], root / "ios", env=env)
        if refreshed.returncode:
            raise IOSLaneError(refreshed.stdout.strip() or "runtime refresh failed")
        return "in-place-cache" if cache.resolve() == target.resolve() else "compatible-cache"

    prepare_env = env.copy()
    cached_archive = cache / "cache/Python-3.13-iOS-support.b14.tar.gz"
    if cached_archive.is_file():
        prepare_env["CABIN_PYTHON_ARCHIVE"] = str(cached_archive)
    prepared = run(["./scripts/prepare_embedded_python.sh"], root / "ios", env=prepare_env)
    if prepared.returncode:
        raise IOSLaneError(prepared.stdout.strip() or "runtime preparation failed")
    return "fresh-prepare"


def available_destination(root: Path, name: str, env: dict[str, str]) -> tuple[str, str]:
    completed = run(["xcrun", "simctl", "list", "devices", "available", "-j"], root, env=env)
    if completed.returncode:
        raise IOSLaneError(completed.stdout.strip() or "simulator discovery failed")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise IOSLaneError(f"simulator discovery returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("devices"), dict):
        raise IOSLaneError("simulator discovery returned an unexpected JSON shape")
    matches: list[tuple[str, str]] = []
    for devices in payload["devices"].values():
        if not isinstance(devices, list):
            raise IOSLaneError("simulator discovery returned an unexpected JSON shape")
        for device in devices:
            if not isinstance(device, dict):
                raise IOSLaneError("simulator discovery returned an unexpected JSON shape")
            if device.get("isAvailable") and device.get("name") == name:
                udid = device.get("udid")
                if isinstance(udid, str) and re.fullmatch(r"[0-9A-F-]+", udid):
                    matches.append((udid, device.get("name", name)))
    if not matches:
        raise IOSLaneError(f"no available iOS Simulator named {name!r}")
    return sorted(matches)[0]


def write_evidence(
    output_dir: Path,
    *,
    status: str,
    command: list[str],
    destination: str,
    detail: str,
    runtime_source: str | None,
    log: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = (output_dir / "ios-test.log").resolve()
    log_path.write_text(log, encoding="utf-8")
    value = {
        "schema_version": 1,
        "status": status,
        "command": command,
        "destination": destination,
        "detail": detail,
        "runtime_source": runtime_source,
        "log_path": str(log_path),
        "log_sha256": sha256(log_path),
    }
    (output_dir / "ios-evidence.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value


def execute(root: Path, cache: Path, output_dir: Path, destination_name: str) -> dict[str, Any]:
    root = root.resolve()
    cache = cache.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("CABIN_LOCAL_OPENAI_API_KEY", None)
    runtime_source: str | None = None
    command: list[str] = []
    try:
        runtime_source = prepare_runtime(root, cache, env)
        udid, name = available_destination(root, destination_name, env)
        derived_data = output_dir / "DerivedData"
        result_bundle = output_dir / "TheCabinTests.xcresult"
        if result_bundle.exists():
            shutil.rmtree(result_bundle)
        command = [
            "xcodebuild",
            "test",
            "-project",
            "ios/TheCabin.xcodeproj",
            "-scheme",
            "TheCabin",
            "-destination",
            f"id={udid}",
            "-derivedDataPath",
            str(derived_data),
            "-resultBundlePath",
            str(result_bundle),
        ]
        completed = run(command, root, env=env)
        status = "passed" if completed.returncode == 0 else "failed"
        detail = (
            "The full iOS XCTest suite passed, including the bundled-Python integration test."
            if status == "passed"
            else f"xcodebuild exited with status {completed.returncode}."
        )
        return write_evidence(
            output_dir,
            status=status,
            command=command,
            destination=name,
            detail=detail,
            runtime_source=runtime_source,
            log=completed.stdout,
        )
    except (IOSLaneError, OSError) as exc:
        return write_evidence(
            output_dir,
            status="unavailable",
            command=[],
            destination=destination_name,
            detail=str(exc),
            runtime_source=runtime_source,
            log=str(exc) + "\n",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--destination", default="iPhone Air")
    args = parser.parse_args()
    value = execute(
        Path(args.root).expanduser(),
        Path(args.cache_root).expanduser(),
        Path(args.output_dir).expanduser(),
        args.destination,
    )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
