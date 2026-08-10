# Codex Instructions

Read `CONTRIBUTING.md` completely before making code, narrative, documentation,
or workflow changes in this repository. It is the canonical source for shared
project guidance. This file contains only the Codex-specific overlay.

## Codex review tools

The required tests, local domain reviews, rerun boundary, and stacked pull
request rules live in `CONTRIBUTING.md`. Do not copy them here.

Follow the review scale in `CONTRIBUTING.md`:

- Every agent-authored pull request gets one outside read of the exact current
  head by a reviewer outside every authoring family. A single pass is the
  default; an empty review completes the step. Loop with the user-level
  `copilot-pr-review-loop` only while passes return findings that change
  behaviour.
- Use the user-level `adversarial-review` skill when the change touches a
  high-risk review boundary in `CONTRIBUTING.md`, or when the maintainer
  requests an independent execution review. Skip it otherwise.
- Do not request `@codex review` by default or block pull request readiness on a
  second hosted Codex review when Copilot already supplies the independent lane.
- Run the review loop in draft, mark the pull request ready for review once
  the outside read and CI are green, and never merge unless explicitly asked.

These review tools do not replace the repository's tests or local domain
reviews. The maintainer is the deciding voice.
