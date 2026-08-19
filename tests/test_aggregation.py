from dataclasses import replace

from oma.aggregation import (
    AggregationDecision,
    AggregationItem,
    AggregationPolicy,
    aggregation_root,
    evaluate_aggregation,
)


def base():
    policy = AggregationPolicy(
        aggregation_policy_id="agg:v1",
        expected_evidence_set_id="set:v1",
        expected_evidence_ids=frozenset({"e1", "e2"}),
        subject_id="s",
        subject_state_id="st",
        verification_context_id="v",
        policy_bundle_id="p",
        pair_id="pair",
        run_id="run",
    )
    items = (
        AggregationItem("e1", "d1", "s", "st", "v", "p", "pair", "run", True),
        AggregationItem("e2", "d2", "s", "st", "v", "p", "pair", "run", True),
    )
    return policy, items


def test_exact_precommitted_set_allows():
    assert evaluate_aggregation(*base()).decision is AggregationDecision.ALLOW


def test_root_is_deterministic_and_order_independent():
    policy, items = base()
    assert aggregation_root(policy, items) == aggregation_root(policy, tuple(reversed(items)))


def test_missing_expected_evidence_is_not_done():
    policy, items = base()
    assert evaluate_aggregation(policy, items[:1]).decision is AggregationDecision.NOT_DONE


def test_failed_expected_evidence_is_not_done():
    policy, items = base()
    result = evaluate_aggregation(policy, (items[0], replace(items[1], passed=False)))
    assert result.decision is AggregationDecision.NOT_DONE


def test_extra_evidence_blocks_cherry_pick_surface():
    policy, items = base()
    extra = replace(items[0], evidence_id="e3")
    assert evaluate_aggregation(policy, items + (extra,)).decision is AggregationDecision.BLOCK


def test_duplicate_evidence_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, items + (items[0],)).decision is AggregationDecision.BLOCK


def test_subject_mismatch_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], subject_id="x"), items[1])).decision is AggregationDecision.BLOCK


def test_state_mismatch_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], subject_state_id="x"), items[1])).decision is AggregationDecision.BLOCK


def test_verification_context_mismatch_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], verification_context_id="x"), items[1])).decision is AggregationDecision.BLOCK


def test_policy_bundle_mismatch_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], policy_bundle_id="x"), items[1])).decision is AggregationDecision.BLOCK


def test_pair_mismatch_blocks_cross_pair_reuse():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], pair_id="other"), items[1])).decision is AggregationDecision.BLOCK


def test_run_mismatch_blocks_cross_run_reuse():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], run_id="other"), items[1])).decision is AggregationDecision.BLOCK


def test_missing_payload_digest_blocks():
    policy, items = base()
    assert evaluate_aggregation(policy, (replace(items[0], payload_digest=""), items[1])).decision is AggregationDecision.BLOCK


def test_empty_expected_set_blocks():
    policy, items = base()
    assert evaluate_aggregation(replace(policy, expected_evidence_ids=frozenset()), items).decision is AggregationDecision.BLOCK


def test_missing_expected_set_id_blocks():
    policy, items = base()
    assert evaluate_aggregation(replace(policy, expected_evidence_set_id=""), items).decision is AggregationDecision.BLOCK


def test_missing_policy_id_blocks():
    policy, items = base()
    assert evaluate_aggregation(replace(policy, aggregation_policy_id=""), items).decision is AggregationDecision.BLOCK


def test_best_of_n_cannot_drop_failed_expected_evidence():
    policy, items = base()
    failed = replace(items[0], passed=False)
    successful_alt = replace(items[0], evidence_id="e3", payload_digest="d3", passed=True)
    assert evaluate_aggregation(policy, (failed, items[1], successful_alt)).decision is AggregationDecision.BLOCK


def test_best_of_n_cannot_replace_failed_expected_evidence():
    policy, items = base()
    replacement = replace(items[0], evidence_id="e3", payload_digest="d3", passed=True)
    assert evaluate_aggregation(policy, (replacement, items[1])).decision is AggregationDecision.BLOCK


def test_same_evidence_set_different_run_changes_root():
    policy, items = base()
    other_policy = replace(policy, run_id="run2")
    other_items = tuple(replace(item, run_id="run2") for item in items)
    assert aggregation_root(policy, items) != aggregation_root(other_policy, other_items)
