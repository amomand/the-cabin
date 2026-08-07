"""Integrity tests for the fixed offline command-interpretation corpus."""

from tools.command_interpretation_eval import DEFAULT_CORPUS, evaluate, load_corpus


def test_corpus_ids_are_unique_and_required_categories_are_present():
    corpus = load_corpus(DEFAULT_CORPUS)
    cases = corpus["cases"]
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))
    assert {
        "ordinary",
        "articles",
        "misspelling",
        "dawn_offer",
        "impossible_target",
        "unknown_item",
        "unavailable_item",
        "model_validation",
        "model_boundary",
    } <= {case["category"] for case in cases}


def test_corpus_runs_without_network_and_reports_every_case():
    corpus = load_corpus(DEFAULT_CORPUS)
    report = evaluate(corpus)

    assert report["total_cases"] == len(corpus["cases"])
    assert len(report["cases"]) == len(corpus["cases"])
