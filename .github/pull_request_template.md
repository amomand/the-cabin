## Summary

<!-- Say what changes and why. -->

## Review provenance

- Authoring agent(s): <!-- Replace with Claude, Codex, Copilot, or Human; list every family that authored the change. -->
- Review depth: <!-- Routine / Material / High-risk. Use the strongest lane touched. -->
- Outside read: <!-- Reviewer + reviewed SHA, or N/A for Routine and human-only changes. A maintainer-facing record; the independent-review status verifies the review itself, not this line. -->
- Adversarial review: <!-- Reviewer + target SHA + verdict for High-risk changes, otherwise N/A. -->

## Validation

- [ ] Relevant tests pass, or an `N/A` reason is recorded below.
- [ ] Applicable local diegesis and continuity reviews have run, with verdicts recorded below.
- [ ] Every review finding has a visible reply recording its disposition.

## Validation notes

- Tests:

## Local review verdicts

- Diegesis: `PASS` / `CONCERN` / `BLOCKER` / `N/A` (reason)
- Continuity: `PASS` / `CONCERN` / `BLOCKER` / `N/A` (reason)

## Stacked PR safety

<!-- Leave this section in place. Mark non-applicable items as N/A with a reason. -->

- [ ] This PR targets `main`, or its feature-branch base is intentional and named in the summary.
- [ ] A stacked child was not merged while GitHub still showed another feature branch as its base.
- [ ] After its parent merged, each child visibly targeted `main`; otherwise it was retargeted manually and its branch was updated before merge.
- [ ] After merge, `python -m tools.verify_main_reachability <child-head-or-feature-commit> [...]` passed against freshly fetched `origin/main`.
- [ ] The post-merge reachability result is recorded in the maintainer update before the stack's tracking issue is closed.
