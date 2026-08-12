# Server surfaces

`server/app.py` exposes the same game over two transports. Both drive the same
`WebGameSession` through the same decoder (`decode_turn_message` in
`server/protocol.py`), so a given input sequence produces identical
`RenderFrame`s on either, and a malformed message is narrated identically on
either. `tests/server/test_http_api.py` asserts both directly.

Parity is at the turn layer, not the transport layer. Session lifetime, error
signalling, and authentication differ by design; those differences are
documented below.

## WebSocket: `/ws`

The browser client (`play.html`). Session lifetime is the socket's lifetime:
the server sends the intro frame on connect, answers each message with a frame,
and releases everything in the connection's `finally` block.

Protected by an `Origin` allowlist (`CABIN_ALLOWED_ORIGINS`), because a browser
attaches ambient credentials to cross-site WebSocket handshakes.

## HTTP: `/session` and `/session/turn`

For native clients. iOS suspends a backgrounded app within seconds and kills
its sockets, so a WebSocket run would end at the first phone lock. The protocol
is strictly request → response, so plain HTTP carries it with no reconnect
logic and no socket to lose.

```
POST /session
  {"client_id": "<optional stable identity>"}
  → 200 {"token": "...", "frame": {...}}

POST /session/turn
  Authorization: Bearer <token>
  {"type": "input", "text": "look"}   or   {"type": "keypress"}
  → 200 {...frame...}
```

The token travels in the `Authorization` header rather than the path, so it
stays out of the request line that servers and proxies log by default. That is
a meaningful reduction, not a guarantee: anything configured to log headers
still sees it.

Errors answer with an HTTP status and a narrated body,
`{"type": "error", "message": "..."}`. No client ever sees framework text.

- `400` malformed body, unusable identity, unknown message type, overlong input
- `403` refused `Origin`
- `404` unknown, expired, or absent token (a missing `Authorization` header is
  answered exactly like a wrong one, so probing cannot distinguish them)
- `409` the identity's existing session is mid-turn; retry when it lands
- `413` body over `MAX_BODY_BYTES`
- `429` at capacity, or rate limited
- `500` a turn raised; the session is released rather than left wedged

Both surfaces enforce the same `Origin` allowlist. The HTTP token is not an
ambient credential, so cross-site request forgery cannot reach a session, but
`POST /session` is reachable without one and every session it mints costs model
credit. The allowlist is there to stop an arbitrary page minting sessions, not
to protect an existing one.

Bodies are read in chunks against `MAX_BODY_BYTES`, and a create reserves its
session slot in the same breath as the capacity check, before the body is read.
Separating those two by an await is what lets concurrent creates all pass a
stale check and overshoot the cap. A create that then fails validation hands
the slot back but keeps its attempt against the per-minute limit, so malformed
bodies are not a free way to probe the endpoint.

### Session lifetime

Sessions live in an in-memory store keyed by token
(`server/session_store.py`), not tied to any connection. A session is released
when it goes idle past `RateLimiter.session_timeout` (default an hour) or when
a frame comes back `game_over`. Expiry is checked on token lookup as well as in
the sweep, so a token cannot be revived by arriving between sweeps. A turn in
progress holds the session open: an in-flight counter blocks expiry, so a slow
model call cannot have the session released out from under it.

Turns are serialised per session by a lock: a double-tapped send must not run
two turns against the same mutable game state.

A `client_id` may hold only one live session at a time. Creating a second one
retires the first, because two sessions writing the same durable save directory
would corrupt each other's saves. If the first is midway through a turn the
create is refused with a `409` instead: retiring it there would leave its
executor still writing the directory the new session is about to claim, which
is the corruption exclusivity exists to prevent. A turn is one model call, so
the client simply retries.

### Saves

Without a `client_id`, a session keeps the throwaway save directory
`WebGameSession` gives itself, deleted when the session is released. That is
the browser's behaviour, unchanged: cleanup simply moved from disconnect to
expiry.

With a `client_id`, saves land in a durable directory that survives session
expiry, so `save` and `load` work across days of phone playtesting. The
identity is hashed (sha256) rather than used as a path segment, so no client
string ever reaches the filesystem. It is a bearer secret in its own right -
anyone holding it can read and overwrite those saves - so it must be 16 to 128
characters of `[A-Za-z0-9._-]`, and a client should generate it once and keep
it somewhere private (on iOS, the keychain).

Durable directories untouched for `CABIN_SAVE_RETENTION_DAYS` (default 30) are
pruned on a timer. Retention is measured from the newest save file in the
directory, and directories belonging to live sessions are excluded from the
sweep outright, so a player mid-run is never collected out from under. A
retention of `0` disables pruning rather than deleting everything.

## Deployment requirements

The HTTP surface holds state the WebSocket surface did not, so the deployment
has to hold it too. Both of these are unmet on the current `fly.toml`; see the
follow-up issue linked from #229.

- The machine must stay running. `auto_stop_machines` plus
  `min_machines_running = 0` stops the machine when the last request drains,
  which is exactly what a backgrounded phone looks like. Every in-memory
  session dies with it.
- `CABIN_SAVE_ROOT` must point at a mounted volume. Without one it resolves
  under the container filesystem, and "durable" saves last only until the next
  deploy.

Until both are true, treat durable saves as durable within a machine's life,
not across it.
