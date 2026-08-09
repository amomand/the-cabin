# Codex Instructions

Read `CONTRIBUTING.md` completely before making code, narrative, documentation,
or workflow changes in this repository. It is the canonical source for shared
project guidance. This file contains only the Codex-specific overlay.

## Codex review tools

The required tests, local domain reviews, rerun boundary, and stacked pull
request rules live in `CONTRIBUTING.md`. Do not copy them here.

Additional review is need-driven:

- Use the user-level `adversarial-review` skill when the maintainer requests an
  independent second-model review. Also offer it before publishing material
  changes with meaningful failure modes, especially changes touching the
  high-risk review boundaries in `CONTRIBUTING.md`. Skip it for copy-only or
  mechanical changes unless the maintainer explicitly asks.
- Use the user-level `copilot-pr-review-loop` skill only when the maintainer asks
  to put an existing pull request through a Copilot review cycle. Follow its
  bounded loop and never merge unless explicitly asked.
- Do not request `@codex review` by default or block pull request readiness on a
  hosted Codex review.

These optional tools do not replace the repository's tests or local domain
reviews. The maintainer is the deciding voice.
