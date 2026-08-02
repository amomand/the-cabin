"""
Tests for explicit environment loading (issue #178).

Importing the game package must not apply .env as a side effect. A harness that
pops OPENAI_API_KEY to force an offline run has to stay offline. These run in a
subprocess with a throwaway .env, because the contract is about import time and
cannot be observed once this process has already imported the package.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "CABIN_TEST_DOTENV_SENTINEL"


def _run_in(tmp_path: Path, source: str) -> str:
    """Run *source* with tmp_path as the working directory and repo on the path."""
    env = {k: v for k, v in os.environ.items() if k != SENTINEL}
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def dotenv_dir(tmp_path: Path) -> Path:
    """A working directory holding a .env nothing else will pick up."""
    (tmp_path / ".env").write_text(
        f"{SENTINEL}=loaded\nOPENAI_TIMEOUT_SECONDS=45\n", encoding="utf-8"
    )
    return tmp_path


class TestImportSideEffects:
    """Importing the game package leaves the environment alone."""

    def test_importing_game_does_not_load_dotenv(self, dotenv_dir):
        """The obvious way to force an offline run has to actually work."""
        output = _run_in(
            dotenv_dir,
            f"""
            import os
            import game.game_engine  # noqa: F401
            print(os.environ.get("{SENTINEL}", "unset"))
            """,
        )

        assert output == "unset"

    def test_importing_ai_interpreter_does_not_load_dotenv(self, dotenv_dir):
        """The interpreter is the module that used to do it at import scope."""
        output = _run_in(
            dotenv_dir,
            f"""
            import os
            import game.ai_interpreter  # noqa: F401
            print(os.environ.get("{SENTINEL}", "unset"))
            """,
        )

        assert output == "unset"


class TestLoadGameDotenv:
    """The explicit loader entry points call."""

    def test_loads_dotenv_when_called(self, dotenv_dir):
        """Entry points opt in, and get the file."""
        output = _run_in(
            dotenv_dir,
            f"""
            import os
            from game.env import load_game_dotenv
            load_game_dotenv()
            print(os.environ.get("{SENTINEL}", "unset"))
            """,
        )

        assert output == "loaded"

    def test_returns_none_without_a_dotenv(self, tmp_path):
        """Nothing to find is not an error."""
        output = _run_in(
            tmp_path,
            """
            from game.env import load_game_dotenv
            print(load_game_dotenv())
            """,
        )

        assert output == "None"

    def test_does_not_override_the_existing_environment(self, dotenv_dir):
        """An exported value beats the file, so harnesses stay in control."""
        output = _run_in(
            dotenv_dir,
            f"""
            import os
            os.environ["{SENTINEL}"] = "exported"
            from game.env import load_game_dotenv
            load_game_dotenv()
            print(os.environ["{SENTINEL}"])
            """,
        )

        assert output == "exported"

    def test_runs_before_module_scope_environment_reads(self, dotenv_dir):
        """The loader must not drag in a module that reads env while importing.

        game.env imports nothing else from the package, so an entry point can
        call it before ai_interpreter freezes OPENAI_TIMEOUT_SECONDS. This is
        the import order server/app.py uses.
        """
        output = _run_in(
            dotenv_dir,
            """
            import os
            os.environ.pop("OPENAI_TIMEOUT_SECONDS", None)
            from game.env import load_game_dotenv
            load_game_dotenv()
            import game.ai_interpreter as ai
            print(ai.OPENAI_TIMEOUT_SECONDS)
            """,
        )

        assert output == "45.0"
