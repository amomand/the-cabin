"""Verify that intended commits have actually reached origin/main."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _error(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr or result.stdout).strip()


def verify_main_reachability(revisions: Sequence[str]) -> bool:
    """Fetch origin/main and report whether each revision is its ancestor."""
    fetched = _git("fetch", "origin", "main")
    if fetched.returncode != 0:
        print(f"Could not fetch origin/main: {_error(fetched)}", file=sys.stderr)
        return False

    all_reachable = True
    for revision in revisions:
        resolved = _git("rev-parse", "--verify", f"{revision}^{{commit}}")
        if resolved.returncode != 0:
            print(f"NOT FOUND  {revision}: {_error(resolved)}", file=sys.stderr)
            all_reachable = False
            continue

        commit = resolved.stdout.strip()
        reachability = _git("merge-base", "--is-ancestor", commit, "origin/main")
        if reachability.returncode == 0:
            print(f"REACHABLE  {revision} ({commit})")
        elif reachability.returncode == 1:
            print(f"NOT REACHABLE  {revision} ({commit})", file=sys.stderr)
            all_reachable = False
        else:
            print(
                f"CHECK FAILED  {revision}: {_error(reachability)}",
                file=sys.stderr,
            )
            all_reachable = False

    return all_reachable


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch origin/main and verify that each commit is reachable from it.",
    )
    parser.add_argument(
        "revisions",
        nargs="+",
        help="Commit SHAs or revision names that must have reached origin/main.",
    )
    args = parser.parse_args(argv)
    return 0 if verify_main_reachability(args.revisions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
