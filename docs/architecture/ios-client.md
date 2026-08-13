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
  TheCabin/
    TheCabinApp.swift     entry point, scene phase
    GameSession.swift     the run as the screen sees it
    Model/                RenderFrame, Status, the client's own narration
    Transport/            the GameTransport boundary and its HTTP conformer
    Store/                keychain identity, transcript on disk
    Views/                transcript, status line, input bar, theme
  TheCabinTests/          unit tests, including a scripted stub transport
```

## The transport boundary

`GameTransport` is the whole of what the UI knows about where frames come from.
`ServerTransport` conforms to it over HTTP today; an on-device engine (#225,
#226) conforms to it later, and no view changes when it does.

The handle a transport exposes for resuming a run is deliberately opaque. The
server transport keeps a session token and the next turn id there; an embedded
engine would keep a save slot. The persistence layer stores whatever it is
given without looking inside. Bare tokens written by the MVP remain readable
and begin their idempotent sequence at one.

Every mobile turn carries that monotonically increasing id. A network failure,
an unreadable 200 response, a 409, or a 429 is retried at most twice inside the
existing 45-second client budget, always with the same id and body. A 409 gets
a short wait; a 429 gets a longer one. Failures known not to have sent anything
and failures that may have lost only the response are distinguished, although
both are safe to repeat once the server can replay the id.

If the bounded attempts still yield no frame, the exact pending turn is already
on disk. The screen shows the existing narrated refusal and a tap cursor; that
tap repeats the pending turn rather than accepting another command. This also
covers a force-quit while a request is in flight. A successful frame clears the
pending turn and advances the id. `waitsForConnectivity` remains off: the
explicit deadline and retry schedule keep the wait bounded and observable in
tests instead of handing an open-ended connectivity wait to `URLSession`.

## Playing across a locked phone

iOS suspends a backgrounded app within seconds, which is why the transport is
HTTP: there is no socket to lose, and the token is still good when the app comes
back.

Two things follow from that:

- **The screen is restored from disk before any request.** The transcript, the
  status line, and the token are written after every frame, so a relaunch shows
  the run immediately rather than an empty screen waiting on the network.
- **Coming back to the foreground checks the run is still there**, by sending an
  empty command. A blank command is not a turn: the session returns a bare
  prompt frame without reaching the interpreter, so the check costs no model
  call and moves nothing. It is only safe while the run wants input — a run
  waiting on a keypress would read the check as the keypress — and it is skipped
  entirely within 30 seconds of the last exchange, because a run cannot expire
  in the time it takes to switch apps.

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

## Identity and durable saves

A `client_id` is minted once per install and kept in the keychain. It is a
bearer secret: anyone holding it can read and overwrite that install's saves.
Sending it with a session create gives a save directory that outlives the
session, which is what makes `save` and `load` work across days of phone
playtesting.

## Diegesis

The client renders frames verbatim and authors almost nothing. Refusals from the
server arrive already narrated and are shown as prose, dimmed rather than boxed
or reddened. The three lines the client does own are in `Model/Narration.swift`,
and cover only the failures the server never gets to speak for: a request that
never arrived, an answer that came back unreadable, and a run this client
already knows it has lost. Where no words are needed — waiting for a keypress,
waiting on a turn — a cursor does the work instead.

## Running it

Open `ios/TheCabin.xcodeproj` and run, or from `ios/`:

```bash
xcodebuild test -scheme TheCabin -destination 'platform=iOS Simulator,name=iPhone Air'
```

The client talks to `https://the-cabin-api.fly.dev` by default. To point a
playtest build at a local server, pass a launch argument:

```
-CabinBaseURL http://127.0.0.1:8080
```

That is the API port, the one `README.md` starts uvicorn on. Port 8000 is the
static site, and a build pointed there gets a 404 with no narrated body for
every request, which surfaces as "the room answers in a shape you cannot read"
with nothing to explain it.

The intro and the first room are authored, so a local server started without an
`OPENAI_API_KEY` is enough to exercise everything up to the first interpreted
command.

Signing for a real device is the one thing not committed here: set the
development team in Xcode against the paid account, which signs for a year.
