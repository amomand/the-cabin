"""Run local playtest scenarios against The Cabin's playable surfaces.

The runner is intentionally local-first: it drives the same terminal/web game
objects a player uses, records visible text, and writes a transcript report.
Scenario files use a small YAML subset so the tool has no runtime dependency
outside the project requirements.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game import game_engine as game_engine_module
from game.ai_interpreter import clear_response_cache
from game.cutscene import CUTSCENE_DISMISS_TEXT
from game.game_engine import GameEngine
from game.persistence import SaveManager
from game.world_state import WorldState
from server.session import SessionPhase, WebGameSession


LIST_KEYS = {"commands", "required_phrases", "forbidden_phrases", "expected_state"}
MAX_WEB_OVERLAYS = 10

# `both` plays the script through the terminal and the web surface together and
# fails if they disagree about anything the player can see. See
# `DifferentialScenarioDriver`.
SURFACES = {"terminal", "web", "both"}
DEFAULT_WEB_SAVE_ROOT = Path("saves") / "web"

DEFAULT_FORBIDDEN_PHRASES = (
    "Invalid command",
    "I don't understand",
    "You can't do that",
    "That is not a valid input",
    "As an AI",
    "Traceback",
    "Error:",
    # The Lyer is never named in player-facing fiction.
    "the Lyer",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    surface: str
    commands: tuple[str, ...]
    description: str = ""
    offline_ai: bool = True
    required_phrases: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = DEFAULT_FORBIDDEN_PHRASES
    # Assertions against the story-state summary, as "key=value" strings.
    expected_state: tuple[str, ...] = ()


@dataclass(frozen=True)
class TranscriptEntry:
    label: str
    lines: tuple[str, ...]


@dataclass
class PlaytestResult:
    scenario: Scenario
    entries: list[TranscriptEntry]
    findings: list[str] = field(default_factory=list)
    # Deterministic story-state summary captured when the scenario closed.
    state: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def transcript_text(self) -> str:
        return "\n".join(
            line for entry in self.entries for line in (entry.label, *entry.lines, "")
        )


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value in {"", '""', "''"}:
        return ""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _strip_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if quote is None and char in {"'", '"'}:
            if index == 0 or line[index - 1].isspace() or line[index - 1] in ":-":
                quote = char
        elif quote == char:
            quote = None
        elif char == "#" and quote is None and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def _string_list(data: dict[str, object], key: str, default: Sequence[str] = ()) -> tuple[str, ...]:
    value = data.get(key, list(default))
    if not isinstance(value, list):
        raise ValueError(f"{key!r} must be a list")
    return tuple(str(item) for item in value)


def load_scenario(path: Path) -> Scenario:
    """Load a scenario file using the runner's small YAML subset."""
    data: dict[str, object] = {}
    current_list: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = _strip_comment(raw_line).rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            if current_list is None:
                raise ValueError(f"{path}: list item without a key: {raw_line!r}")
            existing = data.setdefault(current_list, [])
            if not isinstance(existing, list):
                raise ValueError(f"{path}: key {current_list!r} is not a list")
            existing.append(str(_parse_scalar(stripped[2:])))
            continue

        if ":" not in stripped:
            raise ValueError(f"{path}: expected 'key: value': {raw_line!r}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"{path}: empty key")

        if value:
            data[key] = _parse_scalar(value)
            current_list = None
        elif key in LIST_KEYS:
            data[key] = []
            current_list = key
        else:
            data[key] = ""
            current_list = None

    try:
        name = str(data["name"])
        surface = str(data["surface"])
        commands = _string_list(data, "commands")
    except KeyError as exc:
        raise ValueError(f"{path}: missing required key {exc.args[0]!r}") from exc

    if surface not in SURFACES:
        raise ValueError(
            f"{path}: surface must be one of {', '.join(sorted(SURFACES))}"
        )
    if not commands:
        raise ValueError(f"{path}: commands must not be empty")
    offline_ai = data.get("offline_ai", True)
    if not isinstance(offline_ai, bool):
        raise ValueError(f"{path}: offline_ai must be true or false")

    required = _string_list(data, "required_phrases")
    forbidden = _string_list(data, "forbidden_phrases", DEFAULT_FORBIDDEN_PHRASES)
    expected_state = _string_list(data, "expected_state")
    for expectation in expected_state:
        key, separator, _ = expectation.partition("=")
        if not separator or not key.strip():
            raise ValueError(
                f"{path}: expected_state entries must be 'key=value': {expectation!r}"
            )

    return Scenario(
        name=name,
        surface=surface,
        commands=commands,
        description=str(data.get("description", "")),
        offline_ai=offline_ai,
        required_phrases=required,
        forbidden_phrases=forbidden,
        expected_state=expected_state,
    )


@contextlib.contextmanager
def _offline_ai(enabled: bool) -> Iterator[None]:
    original = os.environ.get("OPENAI_API_KEY")
    if enabled:
        os.environ.pop("OPENAI_API_KEY", None)
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original


def _capture_stdout(fn) -> list[str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fn()
    return buffer.getvalue().splitlines()


@contextlib.contextmanager
def _nonblocking_terminal_keypress() -> Iterator[None]:
    """Let terminal-only engine methods render without waiting for a real key."""

    class FakeStdin:
        def fileno(self) -> int:
            return 0

        def read(self, size: int = -1) -> str:
            return "\n"

    original_stdin = game_engine_module.sys.stdin
    original_tcgetattr = game_engine_module.termios.tcgetattr
    original_tcsetattr = game_engine_module.termios.tcsetattr
    original_setraw = game_engine_module.tty.setraw

    game_engine_module.sys.stdin = FakeStdin()  # type: ignore[assignment]
    game_engine_module.termios.tcgetattr = lambda fd: None  # type: ignore[assignment]
    game_engine_module.termios.tcsetattr = lambda fd, when, settings: None  # type: ignore[assignment]
    game_engine_module.tty.setraw = lambda fd: None  # type: ignore[assignment]
    try:
        yield
    finally:
        game_engine_module.sys.stdin = original_stdin
        game_engine_module.termios.tcgetattr = original_tcgetattr
        game_engine_module.termios.tcsetattr = original_tcsetattr
        game_engine_module.tty.setraw = original_setraw


def _safe_report_stem(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return safe or "scenario"


_WORLD_STATE_FIELDS = {f.name for f in fields(WorldState)}


def _story_state_summary(player, game_map, ended: bool) -> dict[str, str]:
    """Snapshot the story-relevant engine state as ordered, greppable lines.

    Values are rendered as stable strings so scenario `expected_state`
    assertions and downstream transcript readers can compare them directly.
    """
    world = game_map.world_state

    def flag(value: object) -> str:
        return "true" if bool(value) else "false"

    def joined(values: list[str]) -> str:
        return ", ".join(values) if values else "none"

    anomalies = [
        entry.anomaly_id
        for entry in sorted(world.wrongness.entries, key=lambda e: e.seen_at)
    ]
    custom_flags = [
        f"{key}={value}"
        for key, value in sorted(world.to_dict().items())
        if key not in _WORLD_STATE_FIELDS
    ]

    return {
        "room": game_map.current_room.id,
        "ended": flag(ended),
        "health": str(player.health),
        "fear": str(player.fear),
        "inventory": joined([item.name for item in player.inventory]),
        "world_layer": world.world_layer,
        "reunion_stage": world.reunion_stage,
        "ending": world.ending,
        "lyer_encountered": flag(world.lyer_encountered),
        "recognition": flag(world.recognition),
        "consent_given": flag(world.consent_given),
        "wrong_outside_seen": flag(world.wrong_outside_seen),
        "has_power": flag(world.has_power),
        "fire_lit": flag(world.fire_lit),
        "voicemail_heard": flag(world.voicemail_heard),
        "footage_reviewed": flag(world.footage_reviewed),
        "sauna_used": flag(world.sauna_used),
        "first_morning": flag(world.first_morning),
        "wrongness_count": str(world.wrongness.count()),
        "wrongness": joined(anomalies),
        "custom_flags": joined(custom_flags),
    }


class TerminalScenarioDriver:
    def __init__(self) -> None:
        self.engine = GameEngine()
        # Sandbox saves. `GameEngine` builds `SaveManager()` unconditionally,
        # which defaults to `./saves` relative to cwd, so a scenario with a
        # `save` command wrote into the repo's real save directory while the
        # web driver wrote to a tempdir. Harmless while only one terminal
        # scenario existed; not harmless once a differential scenario saves on
        # both surfaces and expects the same answer.
        self._tempdir = tempfile.TemporaryDirectory(prefix="cabin-playtest-term-")
        self.engine.save_manager = SaveManager(
            save_dir=Path(self._tempdir.name) / "saves"
        )
        self.engine.clear_terminal = lambda: None  # type: ignore[method-assign]
        self._real_show_map = self.engine._show_map
        self._real_show_quest_screen = self.engine._show_quest_screen
        self.engine._show_map = self._show_map_once  # type: ignore[method-assign]
        self.engine._show_quest_screen = self._show_quest_screen_once  # type: ignore[method-assign]
        for cutscene in self.engine.cutscene_manager.cutscenes:
            cutscene.play = self._cutscene_play_once(cutscene)  # type: ignore[method-assign]

    def close(self) -> None:
        self._tempdir.cleanup()

    def _show_map_once(self) -> None:
        with _nonblocking_terminal_keypress():
            self._real_show_map()

    def _show_quest_screen_once(self, custom_text: str | None = None) -> None:
        with _nonblocking_terminal_keypress():
            self._real_show_quest_screen(custom_text)

    @staticmethod
    def _cutscene_play_once(cutscene):
        def play() -> None:
            print(cutscene.text)
            print()
            print(CUTSCENE_DISMISS_TEXT)
            cutscene.has_played = True

        return play

    def start(self) -> list[TranscriptEntry]:
        with _nonblocking_terminal_keypress():
            intro = _capture_stdout(self.engine._show_intro)
        rendered = _capture_stdout(self.engine.render)
        return [
            TranscriptEntry("## Intro", tuple(intro)),
            TranscriptEntry("## Initial room", tuple(rendered)),
        ]

    def send(self, command: str) -> list[TranscriptEntry]:
        def turn() -> None:
            self.engine.handle_user_input(command)
            if self.engine.running:
                self.engine.render()

        lines = _capture_stdout(turn)
        return [TranscriptEntry(f"## > {command}", tuple(lines))]

    def state_summary(self) -> dict[str, str]:
        return _story_state_summary(
            self.engine.player, self.engine.map, ended=not self.engine.running
        )


class WebScenarioDriver:
    def __init__(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory(prefix="cabin-playtest-")
        self.session = WebGameSession()
        default_save_dir = self.session.save_manager.save_dir
        self.session.save_manager = SaveManager(
            save_dir=Path(self._tempdir.name) / "saves"
        )
        _remove_default_web_save_dir(default_save_dir)

    def close(self) -> None:
        self._tempdir.cleanup()

    def start(self) -> list[TranscriptEntry]:
        intro = self.session.get_intro_frame()
        room = self.session.handle_input("")
        return [
            TranscriptEntry("## Intro", tuple(intro.lines)),
            TranscriptEntry("## Initial room", tuple(room.lines)),
        ]

    def send(self, command: str) -> list[TranscriptEntry]:
        entries: list[TranscriptEntry] = []
        frame = self.session.handle_input(command)
        entries.append(TranscriptEntry(f"## > {command}", tuple(frame.lines)))

        overlay_count = 0
        while frame.wait_for_key:
            overlay_count += 1
            if overlay_count > MAX_WEB_OVERLAYS:
                raise RuntimeError(
                    f"web overlay limit exceeded after {MAX_WEB_OVERLAYS} dismissals"
                )
            frame = self.session.handle_input("")
            entries.append(
                TranscriptEntry(
                    f"## Auto-dismiss overlay {overlay_count}",
                    tuple(frame.lines),
                )
            )
        return entries

    def state_summary(self) -> dict[str, str]:
        return _story_state_summary(
            self.session.player,
            self.session.map,
            ended=self.session.phase is SessionPhase.ENDED,
        )


TERMINAL_ONLY_PROMPT = "What would you like to do?"

# `list saves` prints each slot's save time. The two surfaces save into separate
# sandboxes microseconds apart, so the stamps differ by construction and say
# nothing about whether the surfaces agree. Mask them; the slot names either
# side still have to match.
_SAVE_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+")


def _normalise_surface_output(entries: Sequence[TranscriptEntry]) -> str:
    """Reduce one command's output to text that both surfaces should agree on.

    The two surfaces present the same turn differently, and none of these
    differences are things the player could call a disagreement:

    - **Line wrapping.** The terminal prints authored cutscene text with its
      hard wraps; the web joins continuation lines into paragraphs. Joining
      everything into one whitespace-collapsed string makes wrapping invisible.
    - **Entry cardinality.** The terminal emits one entry per command because
      cutscenes print inline mid-turn; the web emits the command frame plus one
      per queued overlay plus the room re-render. Concatenating a command's
      entries puts them back on equal terms.
    - **The prompt.** The terminal prints "What would you like to do?" after
      every render; the web carries it in `RenderFrame.prompt`, out of the
      transcript entirely.
    - **Emphasis.** The web wraps overlay cues in asterisks (`*Pull yourself
      back.*`); the terminal prints them bare.
    - **Save timestamps.** The two surfaces save into separate sandboxes
      microseconds apart, so `list saves` stamps differ by construction.

    Everything that survives this is something a player would notice, which is
    the whole point: what is left is the contract.
    """
    words: list[str] = []
    for entry in entries:
        for line in entry.lines:
            text = line.strip().strip("*").strip()
            if not text or text == TERMINAL_ONLY_PROMPT:
                continue
            words.extend(_SAVE_TIMESTAMP.sub("<time>", text).split())
    return " ".join(words)


def _first_difference(left: str, right: str, window: int = 90) -> str:
    """Return a short, readable excerpt around where two strings first differ."""
    limit = min(len(left), len(right))
    index = next((i for i in range(limit) if left[i] != right[i]), limit)
    start = max(0, index - window // 3)
    return (
        f"at char {index}\n"
        f"      terminal: ...{left[start:index + window]!r}\n"
        f"      web:      ...{right[start:index + window]!r}"
    )


class DifferentialScenarioDriver:
    """Play one command script through both surfaces and compare every turn.

    The promise the game makes is that it is the same thing whichever way you
    play it. `game/turn.py` makes both surfaces *decide* a turn through one
    implementation, and `tests/test_turn_parity.py` pins that at unit level.
    Neither covers rendering, which is where the remaining risk lives.

    This driver closes that: it drives `GameEngine` and `WebGameSession`
    through the same commands and asserts, after every single one, that the
    player-visible text and the full story-state snapshot match. The first time
    the two surfaces disagree about anything a player can see, the scenario
    fails and names the turn.

    The report keeps the web transcript, because it is the more detailed of the
    two — overlays are separate labelled entries there rather than inlined.
    """

    def __init__(self) -> None:
        self.terminal = TerminalScenarioDriver()
        self.web = WebScenarioDriver()

    def close(self) -> None:
        try:
            self.terminal.close()
        finally:
            self.web.close()

    def _compare(self, label: str, terminal_entries, web_entries) -> list[str]:
        findings: list[str] = []

        terminal_text = _normalise_surface_output(terminal_entries)
        web_text = _normalise_surface_output(web_entries)
        if terminal_text != web_text:
            findings.append(
                f"surfaces rendered {label} differently: "
                f"{_first_difference(terminal_text, web_text)}"
            )

        terminal_state = self.terminal.state_summary()
        web_state = self.web.state_summary()
        if terminal_state != web_state:
            drift = sorted(
                f"{key}: terminal={terminal_state.get(key)!r} web={web_state.get(key)!r}"
                for key in set(terminal_state) | set(web_state)
                if terminal_state.get(key) != web_state.get(key)
            )
            findings.append(
                f"surfaces disagreed about story state after {label}: {'; '.join(drift)}"
            )

        return findings

    def start(self) -> tuple[list[TranscriptEntry], list[str]]:
        terminal_entries = self.terminal.start()
        web_entries = self.web.start()
        return web_entries, self._compare("the opening", terminal_entries, web_entries)

    def send_and_compare(self, command: str) -> tuple[list[TranscriptEntry], list[str]]:
        terminal_entries = self.terminal.send(command)
        web_entries = self.web.send(command)
        return web_entries, self._compare(f"{command!r}", terminal_entries, web_entries)

    def state_summary(self) -> dict[str, str]:
        return self.web.state_summary()


def _remove_default_web_save_dir(save_dir: Path) -> None:
    default_root = (Path.cwd() / DEFAULT_WEB_SAVE_ROOT).resolve()
    resolved_save_dir = save_dir.resolve()

    try:
        resolved_save_dir.relative_to(default_root)
    except ValueError:
        return

    for path in (resolved_save_dir, default_root, default_root.parent):
        try:
            path.rmdir()
        except OSError:
            break


def _build_driver(surface: str):
    if surface == "terminal":
        return TerminalScenarioDriver()
    if surface == "both":
        return DifferentialScenarioDriver()
    return WebScenarioDriver()


def run_scenario(scenario: Scenario) -> PlaytestResult:
    clear_response_cache()
    driver = _build_driver(scenario.surface)
    differential = isinstance(driver, DifferentialScenarioDriver)
    entries: list[TranscriptEntry] = []
    findings: list[str] = []
    state: dict[str, str] = {}

    with _offline_ai(scenario.offline_ai):
        try:
            if differential:
                entries, opening_findings = driver.start()
                findings.extend(opening_findings)
            else:
                entries = driver.start()
            for command in scenario.commands:
                if differential:
                    command_entries, drift = driver.send_and_compare(command)
                    findings.extend(drift)
                else:
                    command_entries = driver.send(command)
                entries.extend(command_entries)
                if all(not entry.lines for entry in command_entries):
                    findings.append(f"{command!r} produced no visible output")
        except Exception as exc:  # pragma: no cover - exercised through CLI behavior
            entries.append(
                TranscriptEntry(
                    "## Scenario error",
                    (f"{type(exc).__name__}: {exc}",),
                )
            )
            findings.append(f"scenario crashed: {type(exc).__name__}: {exc}")
        finally:
            try:
                state = driver.state_summary()
            except Exception as exc:
                findings.append(
                    f"story state capture failed: {type(exc).__name__}: {exc}"
                )
            driver.close()

    transcript = "\n".join(line for entry in entries for line in entry.lines)
    for phrase in scenario.required_phrases:
        if phrase not in transcript:
            findings.append(f"required phrase not found: {phrase!r}")
    for phrase in scenario.forbidden_phrases:
        if phrase.lower() in transcript.lower():
            findings.append(f"forbidden phrase found: {phrase!r}")
    for expectation in scenario.expected_state:
        key, _, expected = expectation.partition("=")
        key = key.strip()
        expected = expected.strip()
        actual = state.get(key)
        if actual is None:
            findings.append(f"expected state key not captured: {key!r}")
        elif actual != expected:
            findings.append(
                f"state mismatch: {key} is {actual!r}, expected {expected!r}"
            )

    return PlaytestResult(
        scenario=scenario, entries=entries, findings=findings, state=state
    )


def write_report(result: PlaytestResult, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{_safe_report_stem(result.scenario.name)}.txt"
    status = "PASS" if result.passed else "FAIL"

    lines = [
        f"# Playtest Report: {result.scenario.name}",
        "",
        f"Surface: {result.scenario.surface}",
        f"Result: {status}",
        f"Offline AI: {str(result.scenario.offline_ai).lower()}",
    ]
    if result.scenario.description:
        lines.extend(["", result.scenario.description])

    lines.extend(["", "## Commands"])
    lines.extend(
        f"{index}. {command}"
        for index, command in enumerate(result.scenario.commands, 1)
    )

    lines.extend(["", "## Findings"])
    if result.findings:
        lines.extend(f"- {finding}" for finding in result.findings)
    else:
        lines.append("- None.")

    lines.extend(["", "## Story state at close"])
    if result.state:
        lines.extend(f"{key}: {value}" for key, value in result.state.items())
    else:
        lines.append("- Not captured.")

    lines.extend(["", "## Transcript"])
    for entry in result.entries:
        lines.append("")
        lines.append(entry.label)
        lines.extend(entry.lines)

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _default_scenarios() -> list[Path]:
    return sorted((ROOT / "playtests/scenarios").glob("*.yaml"))


def run(
    paths: Sequence[Path],
    report_dir: Path,
    write_reports: bool = True,
) -> list[PlaytestResult]:
    scenarios = [load_scenario(path) for path in paths]
    results = [run_scenario(scenario) for scenario in scenarios]
    if write_reports:
        for result in results:
            write_report(result, report_dir)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Cabin playtest scenarios.")
    parser.add_argument(
        "scenarios",
        nargs="*",
        type=Path,
        help="Scenario YAML files. Defaults to playtests/scenarios/*.yaml.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "reports/playtests",
        help="Directory for transcript reports.",
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Run scenarios without writing transcript files.",
    )
    args = parser.parse_args(argv)

    paths = list(args.scenarios) or _default_scenarios()
    if not paths:
        print("No playtest scenarios found.", file=sys.stderr)
        return 2

    results = run(paths, report_dir=args.report_dir, write_reports=not args.no_reports)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.scenario.name} ({result.scenario.surface})")
        for finding in result.findings:
            print(f"  - {finding}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
