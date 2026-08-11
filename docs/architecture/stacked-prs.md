# Stacked pull requests

For stacked pull requests, a merged badge is not the completion condition.
Never merge a child while its base still names another feature branch. After
the parent merges, wait until GitHub visibly retargets the child to `main`, or
retarget it manually and update the child branch before merging. GitHub's
retargeting can lag behind the parent merge, which is the dangerous window.

After the stack merges, check every intended child head or feature commit
against a freshly fetched `origin/main`:

```bash
python -m tools.verify_main_reachability <commit> [<commit> ...]
```

Record the passing result in the maintainer update before closing the tracking
issue.
