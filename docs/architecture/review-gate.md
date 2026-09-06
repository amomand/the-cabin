# Hosted review gate

The existing gate distinguishes Claude, Codex, Copilot and Human as authoring/review service categories. Keep the `Authoring agent(s):` line and the write-controlled `review:routine` label consistent with its implementation. Record actual model IDs and providers separately; the gate's service test is not proof of cross-provider independence.

Routine work has advisory hosted review. Reviewed work needs an eligible completed hosted review of the exact current head. An Astra/Sol local review does not by itself satisfy that hosted lane. Changing the required notion of independence needs a coordinated change to gate code, tests and documentation.

The gate re-evaluates on pull-request events and a ten-minute sweep of open PRs. Hosted bot review events do not reliably start workflow runs, so an unchanged head can remain pending until the sweep. A review arriving without a new push should clear within one sweep when the other requirements are met.

The weekly scheduled playtest review is a separate system, never a PR gate. See agentic-playtest-review.md for that contract.
