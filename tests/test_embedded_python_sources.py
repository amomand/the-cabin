from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "ios"
    / "scripts"
    / "verify_embedded_python_sources.sh"
)


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    payload = tmp_path / "payload"
    for root in (repository, payload):
        (root / "game").mkdir(parents=True)
        (root / "server").mkdir()
        (root / "game" / "turn.py").write_text("shared = True\n", encoding="utf-8")
        (root / "server" / "local_engine.py").write_text(
            "shared = True\n", encoding="utf-8"
        )
    (repository / "config.json.example").write_text("{}\n", encoding="utf-8")
    (payload / "config.json").write_text("{}\n", encoding="utf-8")
    return repository, payload


def _verify(repository: Path, payload: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), str(repository), str(payload)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_matching_embedded_python_sources_pass(tmp_path):
    repository, payload = _fixture(tmp_path)

    assert _verify(repository, payload).returncode == 0


def test_stale_embedded_python_sources_fail_with_repair_command(tmp_path):
    repository, payload = _fixture(tmp_path)
    (repository / "server" / "local_engine.py").write_text(
        "shared = False\n", encoding="utf-8"
    )

    result = _verify(repository, payload)

    assert result.returncode == 1
    assert "ios/scripts/prepare_embedded_python.sh" in result.stderr
