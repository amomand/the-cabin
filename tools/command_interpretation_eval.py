"""Deterministic offline evaluation for production command interpretation.

The corpus drives ``game.ai_interpreter.interpret`` in one of two modes:

* ``fallback`` removes the API key and measures the real offline fallback.
* ``model`` installs a local streamed-response stub and records whether the
  production path tried to call it. No network or model is used.

The primary metric is exact action-and-argument accuracy. Routing and accepted
impossible inventory targets are constraints rather than alternate ways to
earn primary-metric credit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import game.ai_interpreter as ai_interpreter


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = REPO_ROOT / "evals" / "command_interpretation_corpus.json"


class _OfflineCompletionStub:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls = 0

    def create(self, **_: Any) -> list[SimpleNamespace]:
        self.calls += 1
        return [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=json.dumps(self.response))
                    )
                ]
            )
        ]


def load_corpus(path: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    raw = path.read_bytes()
    corpus = json.loads(raw)
    corpus["_sha256"] = hashlib.sha256(raw).hexdigest()
    return corpus


def _model_response(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    response = {
        "action": expected["action"],
        "args": deepcopy(expected.get("args", {})),
        "confidence": 0.95,
        "reply": "You act. The cold holds close.",
        "effects": {
            "fear": 0,
            "health": 0,
            "inventory_add": [],
            "inventory_remove": [],
        },
        "rationale": "offline deterministic corpus",
    }
    response.update(deepcopy(case.get("model_return", {})))
    return response


def _run_case(case: dict[str, Any], contexts: dict[str, Any]) -> dict[str, Any]:
    context = deepcopy(contexts[case["context"]])
    completion = _OfflineCompletionStub(_model_response(case))
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=completion)
    )

    old_key = os.environ.get("OPENAI_API_KEY")
    old_openai = ai_interpreter.OpenAI
    old_client_factory = ai_interpreter._get_openai_client
    old_logger = ai_interpreter.log_ai_call
    ai_interpreter.clear_response_cache()

    try:
        ai_interpreter.log_ai_call = lambda *_, **__: None
        if case["mode"] == "model":
            os.environ["OPENAI_API_KEY"] = "offline-command-eval"
            ai_interpreter.OpenAI = object()
            ai_interpreter._get_openai_client = lambda _: fake_client
        elif case["mode"] == "fallback":
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            raise ValueError(f"Unknown evaluation mode: {case['mode']!r}")

        intent = ai_interpreter.interpret(case["input"], context)
    finally:
        if old_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = old_key
        ai_interpreter.OpenAI = old_openai
        ai_interpreter._get_openai_client = old_client_factory
        ai_interpreter.log_ai_call = old_logger
        ai_interpreter.clear_response_cache()

    actual = {"action": intent.action, "args": intent.args}
    expected = case["expected"]
    action_args_correct = actual == expected
    model_called = completion.calls > 0
    routing_correct = model_called == case["expect_model_call"]
    impossible_accepted = bool(
        case.get("impossible_target") and intent.action != "none"
    )

    return {
        "id": case["id"],
        "category": case["category"],
        "actual": actual,
        "expected": expected,
        "action_args_correct": action_args_correct,
        "model_called": model_called,
        "model_call_count": completion.calls,
        "expected_model_call": case["expect_model_call"],
        "routing_correct": routing_correct,
        "impossible_target_accepted": impossible_accepted,
    }


def evaluate(corpus: dict[str, Any]) -> dict[str, Any]:
    results = [_run_case(case, corpus["contexts"]) for case in corpus["cases"]]
    correct = sum(result["action_args_correct"] for result in results)
    total = len(results)
    model_calls = sum(result["model_call_count"] for result in results)

    return {
        "corpus_sha256": corpus["_sha256"],
        "total_cases": total,
        "primary": {
            "metric": "exact_action_and_args_accuracy",
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total, 6) if total else 0.0,
            "failed_case_ids": [
                result["id"] for result in results
                if not result["action_args_correct"]
            ],
        },
        "constraints": {
            "model_bound_calls": model_calls,
            "expected_model_bound_calls": sum(
                case["expect_model_call"] for case in corpus["cases"]
            ),
            "routing_mismatch_case_ids": [
                result["id"] for result in results
                if not result["routing_correct"]
            ],
            "impossible_targets_accepted": sum(
                result["impossible_target_accepted"] for result in results
            ),
            "impossible_target_case_ids": [
                result["id"] for result in results
                if result["impossible_target_accepted"]
            ],
        },
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero unless the primary and constraint metrics are perfect.",
    )
    args = parser.parse_args(argv)

    report = evaluate(load_corpus(args.corpus))
    print(json.dumps(report, indent=2, sort_keys=True))

    if not args.check:
        return 0
    return 0 if (
        report["primary"]["correct"] == report["primary"]["total"]
        and not report["constraints"]["routing_mismatch_case_ids"]
        and report["constraints"]["model_bound_calls"]
        == report["constraints"]["expected_model_bound_calls"]
        and report["constraints"]["impossible_targets_accepted"] == 0
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
