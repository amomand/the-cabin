## Summary

<!-- Say what changes and why. -->

## Validation

- [ ] Relevant tests pass, or an `N/A` reason is recorded below.
- [ ] Applicable local diegesis and continuity reviews have run, with verdicts recorded below.

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
