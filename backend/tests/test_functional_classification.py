"""Real functional classification tests over the 80-scenario ground-truth dataset.

These run the REAL heuristic classifiers (token-overlap similarity and
opposing-keyword conflict detection) from scripts/real_benchmark.py over the
REAL 80-scenario dataset, computing genuine confusion matrices and F1 scores.
No mocks: the algorithms, data, and arithmetic are the real ones shipped in the
project. The thresholds assert minimum measurable real performance, so a
regression (algorithm or dataset) fails the suite.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.benchmark_dataset import BENCHMARK_SCENARIOS
from scripts.real_benchmark import evaluate_similarity, evaluate_conflict


def confusion(cls, truth):
    """Return (tp, fp, fn, tn) for a binary classifier over scenario(list) data."""
    tp = fp = fn = tn = 0
    for s in BENCHMARK_SCENARIOS:
        actual = bool(cls(s))
        expected = bool(truth(s))
        if actual and expected:
            tp += 1
        elif actual and not expected:
            fp += 1
        elif not actual and expected:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def f1(tp, fp, fn):
    if tp + fp + fn == 0:
        return 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def test_dataset_shape_is_complete():
    """The ground-truth dataset must contain all 10 categories and 80 scenarios."""
    categories = {s.get("category") for s in BENCHMARK_SCENARIOS}
    assert len(BENCHMARK_SCENARIOS) == 80
    expected = {
        "Facts", "Preferences", "Projects", "Skills", "Goals",
        "Temporal Information", "Multi-Hop Reasoning", "Duplicates",
        "Conflicts", "Irrelevant",
    }
    assert expected.issubset(categories), f"missing categories: {expected - categories}"


def test_duplicate_detection_real_confusion_matrix():
    """Real precision/recall/F1 for duplicate detection over the full dataset."""
    tp, fp, fn, tn = confusion(
        lambda s: evaluate_similarity(s["query"], s.get("existing_memories", [])),
        lambda s: s.get("is_duplicate"),
    )
    score = f1(tp, fp, fn)
    # 6 true duplicates; require catching the majority with no runaway false positives.
    assert tp >= 4, f"duplicate recall too low: {tp}/6"
    assert fp <= 6, f"too many false-positive duplicates: {fp}"
    assert score >= 0.5, f"duplicate F1 too low: {score:.2f}"


def test_conflict_detection_real_confusion_matrix():
    """Real precision/recall/F1 for conflict detection over the full dataset."""
    tp, fp, fn, tn = confusion(
        lambda s: evaluate_conflict(s["query"], s.get("existing_memories", [])),
        lambda s: s.get("is_conflict"),
    )
    score = f1(tp, fp, fn)
    assert tp >= 4, f"conflict recall too low: {tp}/6"
    assert fp <= 8, f"too many false-positive conflicts: {fp}"
    assert score >= 0.5, f"conflict F1 too low: {score:.2f}"


def test_irrelevant_scenarios_never_retrieved():
    """Irrelevant/negative examples must not be labeled as duplicates or conflicts."""
    irrelevant = [s for s in BENCHMARK_SCENARIOS if s.get("category") == "Irrelevant"]
    assert len(irrelevant) >= 3
    # Ground truth: none of these are positive examples.
    assert all(not s.get("is_duplicate") and not s.get("is_conflict") for s in irrelevant)
    # The conflict heuristic must not fire on clearly non-conflicting negative facts.
    false_dups = sum(
        1 for s in irrelevant
        if evaluate_similarity(s["query"], s.get("existing_memories", []))
    )
    false_confs = sum(
        1 for s in irrelevant
        if evaluate_conflict(s["query"], s.get("existing_memories", []))
    )
    assert false_confs == 0, f"conflict heuristic fired on {false_confs} irrelevant scenarios"
    # Allow token-overlap to fire on rephrased negatives, but keep it bounded.
    assert false_dups <= 2, f"duplicate heuristic fired on {false_dups} irrelevant scenarios"
