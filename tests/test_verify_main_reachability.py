"""Tests for the post-merge origin/main reachability check."""

from subprocess import CompletedProcess

from tools import verify_main_reachability


def _result(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return CompletedProcess(
        args=["git"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_fetches_main_then_accepts_reachable_commits(monkeypatch, capsys):
    calls = []
    results = iter(
        [
            _result(),
            _result(stdout="a" * 40 + "\n"),
            _result(),
            _result(stdout="b" * 40 + "\n"),
            _result(),
        ]
    )

    def fake_git(*args):
        calls.append(args)
        return next(results)

    monkeypatch.setattr(verify_main_reachability, "_git", fake_git)

    assert verify_main_reachability.verify_main_reachability(["child-a", "child-b"])
    assert calls[0] == ("fetch", "origin", "main")
    assert calls[2] == ("merge-base", "--is-ancestor", "a" * 40, "origin/main")
    assert calls[4] == ("merge-base", "--is-ancestor", "b" * 40, "origin/main")
    assert capsys.readouterr().out.count("REACHABLE") == 2


def test_reports_a_commit_that_has_not_reached_main(monkeypatch, capsys):
    results = iter(
        [
            _result(),
            _result(stdout="c" * 40 + "\n"),
            _result(returncode=1),
        ]
    )
    monkeypatch.setattr(
        verify_main_reachability,
        "_git",
        lambda *args: next(results),
    )

    assert not verify_main_reachability.verify_main_reachability(["child"])
    assert "NOT REACHABLE" in capsys.readouterr().err


def test_fetch_failure_stops_before_revision_checks(monkeypatch, capsys):
    calls = []

    def fake_git(*args):
        calls.append(args)
        return _result(returncode=1, stderr="network unavailable")

    monkeypatch.setattr(verify_main_reachability, "_git", fake_git)

    assert not verify_main_reachability.verify_main_reachability(["child"])
    assert calls == [("fetch", "origin", "main")]
    assert "network unavailable" in capsys.readouterr().err


def test_invalid_revision_is_reported_and_other_revisions_continue(monkeypatch, capsys):
    results = iter(
        [
            _result(),
            _result(returncode=128, stderr="unknown revision"),
            _result(stdout="d" * 40 + "\n"),
            _result(),
        ]
    )
    monkeypatch.setattr(
        verify_main_reachability,
        "_git",
        lambda *args: next(results),
    )

    assert not verify_main_reachability.verify_main_reachability(["missing", "child"])
    output = capsys.readouterr()
    assert "NOT FOUND" in output.err
    assert "REACHABLE" in output.out
