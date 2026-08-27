from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_probes.py"
SPEC = importlib.util.spec_from_file_location("cabin_prepare_probes", SCRIPT)
assert SPEC and SPEC.loader
preparer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparer)


class ProbePreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.run_dir = Path(self.tempdir.name) / "run"
        self.root.mkdir()
        self.run_dir.mkdir()
        self.source_sha = "a" * 40
        self.scenarios = [self.run_dir / "one.yaml", self.run_dir / "two.yaml"]
        for index, path in enumerate(self.scenarios):
            path.write_text(f"name: probe-{index}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def fake_module(self, *, surface: str = "both", names: list[str] | None = None):
        def load_scenario(path: Path):
            index = [scenario.resolve() for scenario in self.scenarios].index(path)
            return SimpleNamespace(
                name=names[index] if names else f"probe-{index}",
                surface=surface,
                offline_ai=True,
            )

        def run_scenario(scenario):
            self.assertNotIn("OPENAI_API_KEY", preparer.os.environ)
            self.assertNotIn("CABIN_LOCAL_OPENAI_API_KEY", preparer.os.environ)
            return SimpleNamespace(scenario=scenario, passed=True)

        def write_report(result, report_dir: Path):
            report_dir.mkdir(parents=True, exist_ok=True)
            path = report_dir / f"{result.scenario.name}.txt"
            path.write_text(
                f"# Playtest Report: {result.scenario.name}\n\n"
                f"Surface: {result.scenario.surface}\nResult: PASS\n",
                encoding="utf-8",
            )
            return path

        return types.SimpleNamespace(
            _safe_report_stem=lambda name: re.sub(
                r"[^A-Za-z0-9_-]+", "_", name
            ).strip("_")
            or "scenario",
            load_scenario=load_scenario,
            run_scenario=run_scenario,
            write_report=write_report,
        )

    def fake_git(self, _root: Path, *args: str) -> str:
        if args == ("rev-parse", "HEAD"):
            return self.source_sha
        if args[0] == "status":
            return ""
        raise AssertionError(args)

    def test_runs_and_retains_two_unique_both_surface_probes(self) -> None:
        manifest_path = self.run_dir / "probe-manifest.json"
        with mock.patch.dict(
            preparer.os.environ,
            {
                "OPENAI_API_KEY": "must-not-leak",
                "CABIN_LOCAL_OPENAI_API_KEY": "must-not-leak",
            },
        ):
            with mock.patch.object(preparer, "git", side_effect=self.fake_git):
                with mock.patch.dict(
                    sys.modules,
                    {"tools.playtest_runner": self.fake_module()},
                ):
                    value = preparer.prepare(
                        self.root,
                        self.source_sha,
                        [
                            f"guidance={self.scenarios[0]}",
                            f"save-load={self.scenarios[1]}",
                        ],
                        manifest_path,
                    )
        self.assertEqual([probe["family"] for probe in value["probes"]], ["guidance", "save-load"])
        self.assertTrue(all(probe["runner_returncode"] == 0 for probe in value["probes"]))
        self.assertTrue(manifest_path.is_file())

    def test_rejects_a_probe_that_is_not_both_surface(self) -> None:
        with mock.patch.object(preparer, "git", side_effect=self.fake_git):
            with mock.patch.dict(
                sys.modules,
                {"tools.playtest_runner": self.fake_module(surface="web")},
            ):
                with self.assertRaisesRegex(preparer.ProbeError, "surface: both"):
                    preparer.prepare(
                        self.root,
                        self.source_sha,
                        [
                            f"guidance={self.scenarios[0]}",
                            f"save-load={self.scenarios[1]}",
                        ],
                        self.run_dir / "probe-manifest.json",
                    )

    def test_rejects_report_filename_collisions_before_running_either_probe(self) -> None:
        module = self.fake_module(names=["collision one", "collision@one"])
        with mock.patch.object(preparer, "git", side_effect=self.fake_git):
            with mock.patch.dict(sys.modules, {"tools.playtest_runner": module}):
                with mock.patch.object(module, "run_scenario") as run_scenario:
                    with self.assertRaisesRegex(preparer.ProbeError, "report filenames"):
                        preparer.prepare(
                            self.root,
                            self.source_sha,
                            [
                                f"guidance={self.scenarios[0]}",
                                f"save-load={self.scenarios[1]}",
                            ],
                            self.run_dir / "probe-manifest.json",
                        )
        run_scenario.assert_not_called()
        self.assertFalse((self.root / "reports/probes").exists())


if __name__ == "__main__":
    unittest.main()
