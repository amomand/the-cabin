## Summary

<!-- Say what changes and why. -->

## Review provenance

- Authoring agent(s): <!-- Replace with Claude, Codex, Copilot, or Human; list every family that authored the change. -->
- Change class: <!-- A / B / C / D / E / F -->
- Current-head hosted review: <!-- URL + reviewed SHA, or N/A for a human-only change. -->
- Adversarial review: <!-- Reviewer + target SHA + verdict, or N/A with the policy reason. -->
- Maintainer-ready: No <!-- Change to Yes only after current-head review, CI, and thread disposition. -->

## Validation

- [ ] Relevant tests pass, or an `N/A` reason is recorded below.
- [ ] Applicable local diegesis and continuity reviews have run, with verdicts recorded below.
- [ ] Every hosted-review finding has a visible disposition.
- [ ] Any review-fix commit has received a current-head re-review.

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
