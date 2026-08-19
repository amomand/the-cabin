# iOS client

A sideloaded iPhone app for playing and playtesting The Cabin. It is a third
surface in the same sense as the terminal and the web page: it renders
`RenderFrame`s and sends input, and holds no story truth of its own.

The Swift lives in `ios/` in this repository rather than a repository of its
own, so the client and the protocol it renders move together and there is one
issue tracker for both.

## Layout

```
ios/
  TheCabin.xcodeproj      Xcode project (synchronized folders: new files need no project edit)
  TheCabin-Info.plist     bundle configuration
  scripts/                pinned runtime preparation and Xcode packaging
  EmbeddedPython/         generated CPython, app code, and packages (gitignored)
  TheCabin/
    TheCabinApp.swift     entry point, scene phase
    GameSession.swift     the run as the screen sees it
    Model/                RenderFrame, Status, failures, opener, note context
    Embedded/             serial Objective-C bridge to native CPython
    Transport/            GameTransport, local engine, and retained HTTP conformer
    Store/                keychain identity, run and playtest notes on disk
    Assets.xcassets/      app icon and system accent colour
    Views/                opener, transcript, status line, input bar, theme
  TheCabinTests/          unit tests, including a scripted stub transport
```

## The transport boundary

`GameTransport` is the whole of what the UI knows about where frames come from.
`LocalEngineTransport` is the app's production conformer. It crosses a serial
Objective-C bridge into the bundled CPython runtime, where `LocalEngine` wraps
the same `WebGameSession` used by the server. `ServerTransport` remains as the
tested HTTP conformer, but selecting one or the other changes no view and puts
no story truth in Swift.

The handle a transport exposes for resuming a run is deliberately opaque. The
server transport keeps a session token and the next turn id there; the local
engine keeps a versioned run id and next turn id. The persistence layer stores
whatever it is given without looking inside. Bare server tokens written by the
MVP remain readable by `ServerTransport` and begin their idempotent sequence at
one.

Every mobile turn carries that monotonically increasing id. For HTTP, a network
failure, an unreadable 200 response, a 409, or a 429 is retried at most twice
inside the existing 45-second client budget, always with the same id and body.
A 409 gets a short wait; a 429 gets a longer one. Failures known not to have
sent anything and failures that may have lost only the response are
distinguished, although both are safe to repeat once the server can replay the
id.

If the bounded attempts still yield no frame, the exact pending turn is already
on disk. The screen shows the existing narrated refusal and a tap cursor; that
tap repeats the pending turn rather than accepting another command. This also
covers a force-quit while a request is in flight. A successful frame clears the
pending turn and advances the id. `waitsForConnectivity` remains off: the
explicit deadline and retry schedule keep the wait bounded and observable in
tests instead of handing an open-ended connectivity wait to `URLSession`.

The local adapter checkpoints before returning each completed frame. Its
checkpoint includes the full serializable game state plus the
`WebGameSession` phase, room/feedback render state, queued overlays, and the
last completed turn body and exact frame. Repeating that id and body after an
ambiguous force-quit returns the stored frame without advancing play; reusing
the id with another body fails closed. The current schema is version 1. A
missing, corrupt, malformed, or future-version checkpoint is never partially
loaded.

## Playing across a locked phone

iOS suspends a backgrounded app within seconds. The local engine has no socket
to lose: it atomically replaces its sandbox checkpoint after every frame and
flushes again when the scene leaves the foreground.

Two things follow from that:

- **The run is restored from disk before any request.** Every cold process
  launch first covers it with the authored opener. A tap removes only that
  cover, revealing the exact transcript, status line, and input state restored
  underneath; it sends no turn and cannot dismiss an overlay or retry a pending
  request. Returning from the background in the same process does not replay
  it. No liveness probe runs behind the cover: even a failed probe would mutate
  the prompt and mode before the saved run was revealed. If the saved run is
  itself waiting on the real opening frame, the client renders that frame
  instead of putting an identical cover over it.
- **The cover does not own story truth.** A new run renders the opening
  `RenderFrame` supplied by its transport and caches those exact lines for later
  cold launches. Only run files written before that cache existed use an iOS
  fallback, and an executable parity test holds those bytes to the shared
  `game.intro.INTRO_LINES` canon used by both Python engine surfaces.
- **Coming back to the foreground checks the run is still readable** without
  advancing it. The local probe validates the adopted checkpoint; the retained
  HTTP transport sends an empty command. A blank command is not a turn: the
  session returns a bare prompt frame without reaching the interpreter, so the
  check costs no model call and moves nothing. It is only safe while the run
  wants input — a run waiting on a keypress would read the check as the keypress
  — and it is skipped entirely within 30 seconds of the last exchange, because
  a run cannot expire in the time it takes to switch apps.

When a run has genuinely gone (an expired token, or a turn that died), the
client narrates the server's own line and then holds. It does not restart under
the player: the intro frame clears the screen, so opening a new run there would
wipe the line still being read. The next tap opens one, and because the intro is
authored prose it reads as the restart without the client writing one. Durable
saves outlive the session, so `load` works from there.

## Status line

Health and fear have no structured channel: the turn core appends a formatted
line to every room render, and the browser client scrapes it the same way. The
client parses that line, pins it above the transcript, and keeps it out of the
prose. A line that fails to parse is left in the transcript untouched, so a
change of format upstream loses the pinning rather than the text.

## Command line

The input bar is one row: the server's prompt prefix and a single-line field on
a shared centre line. The keyboard never rises on its own. It drops when a
command is sent and whenever the run stops asking for one, and comes back only
when the player taps the prompt row or the transcript while a command is
wanted. The reply therefore always lands on a full screen rather than in the
strip above a keyboard, at the cost of one tap per turn. The system keyboard is
kept, rather than a custom input view, because it brings the dictation
microphone with it.

## Pocket notebook

The pencil beside the status line is present throughout the run, including
before there are readings to pin. It opens a local field note and freezes its
context at that instant: the successful player-turn index, health and fear, and
the last eight rendered transcript blocks. Typing for a while does not let the
note quietly drift to a later room.

The turn index belongs to `GameSession`, not either transport. Opening a run and
checking that a suspended run still exists do not advance it. A delivered
keypress or command advances it once. A failed request advances nothing, and a
pending request that succeeds on a later tap or after relaunch advances exactly
once. The counter lives in `run.json`; older files decode at zero.

An on-device engine may also supply a `PlaytestStorySnapshot`. This is a narrow,
sanitised projection of act, location, world layer, and short story markers. It
is not the engine save. Credential-shaped values are dropped at the boundary
and again when notes are decoded.

Kept notes append to `playtest-notes.json` as a versioned structured archive.
The read-modify-write is locked and atomically replaces the file, so quick
successive notes cannot leave half a notebook. An unreadable or truncated
archive is never overwritten. Export rewrites one deterministic Markdown file
from the archive, then gives that local URL to the system share sheet for Files
or AirDrop.

Nothing in this path calls the server, syncs, or files an issue. The note DTO can
only contain its body and the captured context above; it has no field for the
opaque resume handle, keychain `client_id`, an API key, or configuration. Triage
into `[playtest]` issues remains a deliberate job back at the laptop.

## Visual identity

The app icon is a deliberately bare black field with the homepage title in an
old-style serif. Inside the app, prose and input use the iOS-bundled Iowan Old
Style face, with Dynamic Type scaling; the compact health and fear line remains
monospaced. This follows the browser surface's serif prose and monospaced
status treatment without bundling or licensing another font file.

The turn core writes a few lines as a terminal would, and the browser surface
already reads those shapes and styles them. `Model/TranscriptLayout.swift` does
the same for iOS, as a pure function over the stored blocks: a room name before
a row of dashes is set as a heading over a short hairline, a long box-drawing
rule becomes the same hairline, a line wrapped in asterisks is set in italic
with the markers dropped, and an empty line is a paragraph break rather than a
blank row of type. Only the room's own lines take these roles; the player's
echo and narrated refusals are left as they are. Nothing is rewritten or stored
differently, so a run file from before this existed renders the same prose.

## Durable local saves

Checkpoints, named saves, and logs live below the app's Application Support
container, never beside the read-only bundled Python files. Development seeds
remain code-built fixtures, so `load act4_night` and the other named seeds work
without shipping generated save files. On the first private Xcode launch, the
app copies the launch-injected model credential into this install's device-only
Keychain. Later Home-Screen launches restore it into the process environment
before embedded Python starts. XCTest does neither. The credential is not
written into the app bundle, Swift transcript, resume handle, Python checkpoint,
named save, or logs. AI-call payload logging remains off by default.

## Embedded runtime boundary

`ios/scripts/prepare_embedded_python.sh` downloads BeeWare Python Apple Support
`3.13-b14` (Python 3.13.14) and refuses the archive unless its SHA-256 is
`8b5cb76ef8d8a2946052479358eeec9d54b4496cb60920e175ec1489b5cf7963`.
The 115 MB framework is generated under `ios/EmbeddedPython/` and is never
committed.

The mobile dependency set is pinned to pure-Python wheels for httpx and its
dependencies, listed with `--hash=sha256:` lines in `ios/requirements-ios.txt`.
Both the download and the install run with `--require-hashes`, so a wheel that
does not match its pin is refused, including one supplied through
`CABIN_WHEELHOUSE`. Preparation also rejects platform wheels, native
extensions, the OpenAI SDK, and pydantic. Bumping a dependency means updating
the version and hash together in that file. The interpreter uses the direct httpx Chat
Completions shim only when the bridge selects `CABIN_MODEL_TRANSPORT=direct-httpx`;
desktop and server entry points keep the SDK path. Prompt construction,
response validation, deterministic fallbacks, and turn effects remain shared.

The Xcode target disables user-script sandboxing for the packaging phase. The
BeeWare helper discovers version-specific standard-library extensions and
rewrites them into per-module frameworks, so its generated app-bundle outputs
do not have a stable checked-in file list. This is a build-time exception, not
an app entitlement: the tracked phase reads only the checksum-verified runtime
and prepared app roots, writes only the app bundle, and CI prepares that runtime
afresh from the pinned archive.

The packaging phase also compares the checked-out `game/`, `server/`, and
`config.json.example` sources with the ignored prepared payload. A build fails
with the refresh command when that snapshot is stale, so a successful app
cannot silently bundle an older shared engine; the phase never re-syncs on its
own. `ios/scripts/refresh_embedded_sources.sh` re-syncs only that payload and
is the one place the sync is defined; the full prepare script calls it after
laying down the framework and wheels, and it refuses to run if the runtime has
not been prepared.

## Diegesis

The client renders frames verbatim and authors almost nothing. Refusals from the
server arrive already narrated and are shown as prose, dimmed rather than boxed
or reddened. The three lines the client does own are in `Model/Narration.swift`,
and cover only the failures the server never gets to speak for: a request that
never arrived, an answer that came back unreadable, and a run this client
already knows it has lost. Where no words are needed — waiting for a keypress,
waiting on a turn — a cursor does the work instead.

`Model/LaunchOpener.swift` contains the legacy migration fallback described
above. Those lines are not client-authored: the parity test makes any drift from
the shared Python opener fail CI.

## Running it

Open `ios/TheCabin.xcodeproj` and run, or from `ios/`:

```bash
./scripts/prepare_embedded_python.sh
xcodebuild test -scheme TheCabin -destination 'platform=iOS Simulator,name=iPhone Air'
```

After editing shared Python under `game/`, `server/`, or `config.json.example`,
the next build fails as stale. Re-sync just the payload rather than re-running
the full download and wheel checks:

```bash
./scripts/refresh_embedded_sources.sh
```

The intro, first room, and deterministic rules run without an API key. For a
private simulator or device playtest of free-form model turns, copy
`Local.example.xcconfig` to the gitignored `Local.xcconfig` and set
`CABIN_LOCAL_OPENAI_API_KEY` there. The shared Xcode scheme expands it only into
`OPENAI_API_KEY` in the app's launch environment. The app captures that value
in its device-only Keychain and restores it before the interpreter boots on
later untethered launches; tests explicitly clear it and never read the stored
credential. Never add it to the project, bundle resources, or a committed file.

Signing for a real device is the one thing not committed here: set the
development team in Xcode against the paid account, which signs for a year.
Physical-device launch, suspend/force-quit recovery, memory pressure, and a
live free-form turn using a launch-injected key remain the final phone-only
acceptance boundary.
