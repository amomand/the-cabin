# Codex Instructions

Read `CONTRIBUTING.md` completely before making code, narrative, documentation,
or workflow changes in this repository. It is the canonical source for shared
project guidance. This file contains only the Codex-specific overlay.

## Codex review tools

The required tests, local domain reviews, rerun boundary, and stacked pull
request rules live in `CONTRIBUTING.md`. Do not copy them here.

Use the review tools through their distinct lanes:

- Use the user-level `adversarial-review` skill for every mandatory trigger in
  `CONTRIBUTING.md`, or when the maintainer requests an independent execution
  review. Skip it outside those triggers unless requested.
- For an agent-authored pull request, use the user-level
  `copilot-pr-review-loop` when Copilot is outside every authoring family. If it
  is not eligible, route to another hosted family. Satisfy the current-head
  invariant before calling the draft maintainer-ready, and never merge unless
  explicitly asked.
- Do not request `@codex review` by default or block pull request readiness on a
  second hosted Codex review when Copilot already supplies the independent lane.

These review tools do not replace the repository's tests or local domain
reviews. The maintainer is the deciding voice.
